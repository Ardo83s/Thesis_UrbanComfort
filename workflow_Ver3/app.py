import os
import json
import numpy as np
import flask
import ghhops_server as hs
from shapely.geometry import shape, Point
from rasterio.transform import from_origin
from rasterio.features import rasterize
import rasterio
import tensorflow as tf
import matplotlib.pyplot as plt
import torch
import torch.nn.functional as F
from torch.nn import Linear
from torch_geometric.nn import GATConv
from torch_geometric.data import Data
from PIL import Image

# === Load CNN model (SVF) ===
cnn_model = tf.keras.models.load_model("cnn_svf_model.h5", compile=False)

# === Load GNN model (Tmrt) ===
class TmrtGAT(torch.nn.Module):
    def __init__(self, in_channels=8, hidden_channels=32):
        super().__init__()
        self.gat1 = GATConv(in_channels, hidden_channels, heads=4, concat=True)
        self.gat2 = GATConv(hidden_channels * 4, hidden_channels, heads=4, concat=False)
        self.lin = Linear(hidden_channels, 1)

    def forward(self, x, edge_index):
        x = self.gat1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.gat2(x, edge_index)
        x = F.relu(x)
        x = self.lin(x)
        return x.view(-1)

gnn_model = TmrtGAT(in_channels=8, hidden_channels=32)
gnn_model.load_state_dict(torch.load("gnn_tmrt_model.pth", map_location="cpu"))
gnn_model.eval()

# === Flask + Hops Setup ===
app = flask.Flask(__name__)
hops = hs.Hops(app)

@hops.component(
    "/full_svf_pipeline",
    name="Full SVF + Tmrt Pipeline",
    description="Generates DSM, CDSM, Building Mask, SVF, and Tmrt from GeoJSON",
    inputs=[
        hs.HopsString("Footprints", "Footprints", "Building footprints GeoJSON", access=hs.HopsParamAccess.ITEM),
        hs.HopsString("Trees", "Trees", "Tree GeoJSON with height and radius", access=hs.HopsParamAccess.ITEM),
        hs.HopsString("Extent", "Extent", "GeoJSON defining the bounds", access=hs.HopsParamAccess.ITEM),
        hs.HopsNumber("PixelSize", "PixelSize", "Pixel size (in meters)", access=hs.HopsParamAccess.ITEM),
        hs.HopsString("OutPath", "PathFolder", "Folder to save all output files", access=hs.HopsParamAccess.ITEM),
        hs.HopsString("Green","Green","Green Area", access=hs.HopsParamAccess.ITEM),
        hs.HopsString("Pavement","Pavement","Pavement Area", access=hs.HopsParamAccess.ITEM),
    ],
    outputs=[
        hs.HopsString("Status", "Status", "Success or failure message"),
        hs.HopsString("TmrtPNGPath", "Tmrt PNG", "Path to predicted_tmrt.png"),
        hs.HopsString("TmrtMatrix", "Tmrt Matrix", "2D JSON array of Tmrt values")
    ]
)
def full_pipeline(footprints_str, trees_str, extent_str, pixel_size, out_path, green, pavement):
    try:
        extent = json.loads(extent_str)
        extent_geom = shape(extent["geometry"] if "geometry" in extent else extent["features"][0]["geometry"])
        minx, miny, maxx, maxy = extent_geom.bounds
        cols = rows = 128
        transform = from_origin(minx, maxy, pixel_size, pixel_size)

        # === Parse buildings ===
        footprints = json.loads(footprints_str)
        building_shapes = [
            (shape(f["geometry"]), float(f.get("properties", {}).get("height", 0)))
            for f in footprints.get("features", [])
        ]

        # === Parse trees ===
        trees = json.loads(trees_str)
        tree_shapes = []
        for f in trees.get("features", []):
            props = f.get("properties", {})
            height = float(props.get("height", 5))
            radius = float(props.get("radius", 1.5))
            geom = shape(f["geometry"])
            if isinstance(geom, Point):
                tree_shapes.append((geom.buffer(radius), height))

        # === Rasterize ===
        dsm = rasterize(building_shapes, out_shape=(rows, cols), transform=transform, fill=0, dtype='float32')
        cdsm = rasterize(tree_shapes, out_shape=(rows, cols), transform=transform, fill=0, dtype='float32')
        building_mask = rasterize([s[0] for s in building_shapes], out_shape=(rows, cols), transform=transform,
                                   fill=1, default_value=0, dtype='uint8')

        os.makedirs(out_path, exist_ok=True)

        # === Parse Green and Pavement GeoJSONs ===
        green_areas = json.loads(green)
        pavement_areas = json.loads(pavement)

        green_shapes = [shape(f["geometry"]) for f in green_areas.get("features", [])]
        pavement_shapes = [shape(f["geometry"]) for f in pavement_areas.get("features", [])]

        # === Initialize landuse array
        landuse = np.zeros((rows, cols), dtype=np.uint8)

        # Step 1: Pavement
        if pavement_shapes:
            pavement_mask = rasterize(
                [(g, 1) for g in pavement_shapes],
                out_shape=(rows, cols),
                transform=transform,
                fill=0,
                dtype='uint8'
            )
            landuse[pavement_mask == 1] = 1

        # Step 2: Green 
        if green_shapes:
            green_mask = rasterize(
                [(g, 5) for g in green_shapes],
                out_shape=(rows, cols),
                transform=transform,
                fill=0,
                dtype='uint8'
            )
            landuse[green_mask == 5] = 5

        # Step 3: Buildings
        if building_shapes:
            building_geom = [g[0] for g in building_shapes]
            building_mask = rasterize(
                [(g, 2) for g in building_geom],
                out_shape=(rows, cols),
                transform=transform,
                fill=0,
                dtype='uint8'
            )
            landuse[building_mask == 2] = 2


        def save_raster(path, array, dtype):
            with rasterio.open(
                path, 'w', driver='GTiff', height=rows, width=cols, count=1,
                dtype=dtype, crs='EPSG:25831', transform=transform
            ) as dst:
                dst.write(array, 1)

        def save_png(path, array, cmap="Spectral_r", vmin=15, vmax=40):
            cmap_func = plt.get_cmap(cmap)
            norm = np.clip((array - vmin) / (vmax - vmin), 0, 1)
            rgba = cmap_func(norm)[..., :3]
            img = (rgba * 255).astype(np.uint8)
            with rasterio.open(os.path.join(out_path, "buildings.tif")) as src:
                mask_data = src.read(1)
                img[mask_data == 0] = 255
            Image.fromarray(img).save(path)

        save_raster(os.path.join(out_path, "dsm.tif"), dsm, 'float32')
        save_raster(os.path.join(out_path, "cdsm.tif"), cdsm, 'float32')
        save_raster(os.path.join(out_path, "buildings.tif"), building_mask, 'uint8')
        save_raster(os.path.join(out_path, "combined_landuse.tif"), landuse, 'uint8')

        # === Predict SVF ===
        dsm = np.nan_to_num(dsm)
        cdsm = np.nan_to_num(cdsm)
        dsm /= np.max(dsm) if np.max(dsm) > 0 else 1
        cdsm /= np.max(cdsm) if np.max(cdsm) > 0 else 1

        input_stack = np.stack([dsm, cdsm], axis=-1)
        input_stack = np.expand_dims(input_stack, axis=0)
        svf_pred = cnn_model.predict(input_stack, verbose=0)[0, ..., 0]

        save_raster(os.path.join(out_path, "predicted_svf.tif"), svf_pred, 'float32')
        save_png(os.path.join(out_path, "predicted_svf.png"), svf_pred, cmap="Spectral_r", vmin=15, vmax=40)

        # === Contextual Features ===
        def compute_contextual_features(dsm, buildings, patch_size=8):
            h, w = dsm.shape
            density_map = np.zeros_like(dsm, dtype=np.float32)
            mean_height_map = np.zeros_like(dsm, dtype=np.float32)
            for row in range(0, h, patch_size):
                for col in range(0, w, patch_size):
                    r_end = min(row + patch_size, h)
                    c_end = min(col + patch_size, w)
                    block_dsm = dsm[row:r_end, col:c_end]
                    block_bld = buildings[row:r_end, col:c_end]
                    area = block_dsm.size
                    bld_area = np.sum(block_bld > 0)
                    mean_h = np.mean(block_dsm)
                    density = bld_area / area
                    density_map[row:r_end, col:c_end] = density
                    mean_height_map[row:r_end, col:c_end] = mean_h
            return density_map, mean_height_map

        svf = np.nan_to_num(svf_pred)
        svf = np.clip(svf, 0, 1)
        buildings = np.clip(np.nan_to_num(building_mask), 0, 1)
        density_map, mean_height_map = compute_contextual_features(dsm, buildings)
        h, w = dsm.shape
        xx, yy = np.meshgrid(np.arange(w), np.arange(h))
        x_coord = xx / w
        y_coord = yy / h

        features = [
            dsm, cdsm, svf, x_coord, y_coord, buildings,
            density_map, mean_height_map
        ]
        x = np.stack(features, axis=-1).reshape(-1, len(features))
        edge_index = []
        for row in range(h):
            for col in range(w):
                idx = row * w + col
                if col < w - 1:
                    edge_index.append([idx, idx + 1])
                if row < h - 1:
                    edge_index.append([idx, idx + w])
        edge_index = np.array(edge_index).T

        graph = Data(
            x=torch.tensor(x, dtype=torch.float),
            edge_index=torch.tensor(edge_index, dtype=torch.long)
        )

        with torch.no_grad():
            pred_tmrt = gnn_model(graph.x, graph.edge_index).cpu().numpy().reshape(h, w)

        tmrt_tif_path = os.path.join(out_path, "predicted_tmrt.tif")
        tmrt_png_path = os.path.join(out_path, "predicted_tmrt.png")
        save_raster(tmrt_tif_path, pred_tmrt, 'float32')
        save_png(tmrt_png_path, pred_tmrt, cmap="Spectral_r", vmin=15, vmax=40)


        return f"✅ Saved DSM, CDSM, SVF and Tmrt to {out_path}", tmrt_png_path, json.dumps(pred_tmrt.tolist())

    except Exception as e:
        return f"❌ Error: {str(e)}", "", "[]"

if __name__ == "__main__":
    app.run(debug=True)
