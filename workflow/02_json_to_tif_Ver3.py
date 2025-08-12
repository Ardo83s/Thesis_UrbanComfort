import os
import json
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import Polygon, mapping
import matplotlib.pyplot as plt
import fiona
from fiona.crs import from_epsg

# --- Optional: Set GDAL_DATA for projection definitions ---
QGIS_PATH = r"C:\Program Files\QGIS 3.34.12"
os.environ['GDAL_DATA'] = os.path.join(QGIS_PATH, 'share', 'gdal')

# --- CONFIG ---
input_root = "C:/Users/Ardo/Desktop/thesis/processed"
utm_x_origin = 430000
utm_y_origin = 4580000
CRS = "EPSG:25831"

# --- MAIN LOOP ---
for subfolder in os.listdir(input_root):
    folder_path = os.path.join(input_root, subfolder)
    json_path = os.path.join(folder_path, "street_geo.json")
    geojson_folder = os.path.join(folder_path, "geojson_export")
    os.makedirs(geojson_folder, exist_ok=True)

    if not os.path.isdir(folder_path) or not os.path.exists(json_path):
        continue

    print(f"\n📂 Processing: {subfolder}")

    with open(json_path, "r") as f:
        data = json.load(f)

    cell_size = data["cell_size"]
    plane_width, plane_height = data["plane_size"]
    buildings = data.get("buildings", [])
    street = data.get("street", [])

    cols = int(np.ceil(plane_width / cell_size))
    rows = int(np.ceil(plane_height / cell_size))

    local_transform = from_origin(-plane_width / 2, plane_height / 2, cell_size, cell_size)
    world_x_top_left = utm_x_origin - plane_width / 2
    world_y_top_left = utm_y_origin + plane_height / 2
    world_transform = from_origin(world_x_top_left, world_y_top_left, cell_size, cell_size)

    # --- Rasterize DSM ---
    shapes_and_heights = []
    for b in buildings:
        footprint = b.get("footprint")
        height = float(b.get("height", 0))
        if not footprint or height == 0:
            continue
        poly = Polygon(footprint)
        if poly.is_valid:
            shapes_and_heights.append((poly, height))
        else:
            print(f"⚠️ Invalid polygon skipped in {subfolder}")

    if shapes_and_heights:
        dsm = rasterize(
            shapes=shapes_and_heights,
            out_shape=(rows, cols),
            transform=local_transform,
            fill=0,
            dtype=np.float32,
            all_touched=True
        )
    else:
        print("⚠️ No valid buildings found. Creating empty DSM.")
        dsm = np.zeros((rows, cols), dtype=np.float32)

    # --- Save DSM & DEM ---
    dsm_path = os.path.join(folder_path, "dsm.tif")
    dem_path = os.path.join(folder_path, "dem.tif")
    dsm_npy = os.path.join(folder_path, "dsm.npy")
    dem_npy = os.path.join(folder_path, "dem.npy")

    np.save(dsm_npy, dsm)
    np.save(dem_npy, np.zeros_like(dsm, dtype=np.float32))

    with rasterio.open(
        dsm_path, "w", driver="GTiff", height=rows, width=cols,
        count=1, dtype=dsm.dtype, crs=CRS, transform=world_transform
    ) as dst:
        dst.write(dsm, 1)

    with rasterio.open(
        dem_path, "w", driver="GTiff", height=rows, width=cols,
        count=1, dtype=np.float32, crs=CRS, transform=world_transform
    ) as dst:
        dst.write(np.zeros_like(dsm, dtype=np.float32), 1)

    print("✅ DSM and DEM saved")

    # --- Convert street to UTM polygon ---
    street_geom = None
    if street:
        street_utm_coords = [(utm_x_origin + x, utm_y_origin + y) for x, y in street]
        poly = Polygon(street_utm_coords)
        if poly.is_valid:
            street_geom = mapping(poly)

    # --- Convert buildings to UTM polygons ---
    building_features = []
    for b in buildings:
        footprint = b.get("footprint")
        height = float(b.get("height", 0))
        if footprint and height > 0:
            poly = Polygon([(utm_x_origin + x, utm_y_origin + y) for x, y in footprint])
            if poly.is_valid:
                building_features.append({
                    "geometry": mapping(poly),
                    "properties": {
                        "height": height,
                        "source": subfolder
                    }
                })

    # --- 1️⃣ Export street-only GeoJSON ---
    if street_geom:
        street_path = os.path.join(folder_path, "street.geojson")
        schema = {
            "geometry": "Polygon",
            "properties": {"id": "str"}
        }
        with fiona.open(street_path, "w", driver="GeoJSON", crs=from_epsg(25831), schema=schema) as layer:
            layer.write({
                "geometry": street_geom,
                "properties": {"id": subfolder}
            })

    # --- 2️⃣ Export buildings-only GeoJSON ---
    if building_features:
        bld_path = os.path.join(folder_path, "building.geojson")
        schema = {
            "geometry": "Polygon",
            "properties": {"height": "float", "source": "str"}
        }
        with fiona.open(bld_path, "w", driver="GeoJSON", crs=from_epsg(25831), schema=schema) as layer:
            for feat in building_features:
                layer.write(feat)

    # --- 3️⃣ Export combined GeoJSON ---
    combined_path = os.path.join(folder_path, "total.geojson")
    schema = {
        "geometry": "Polygon",
        "properties": {
            "type": "str",
            "height": "float",
            "source": "str"
        }
    }
    with fiona.open(combined_path, "w", driver="GeoJSON", crs=from_epsg(25831), schema=schema) as layer:
        if street_geom:
            layer.write({
                "geometry": street_geom,
                "properties": {"type": "street", "height": 0.0, "source": subfolder}
            })
        for feat in building_features:
            layer.write({
                "geometry": feat["geometry"],
                "properties": {
                    "type": "building",
                    "height": feat["properties"]["height"],
                    "source": subfolder
                }
            })

    print(f"✅ Exported GeoJSONs for {subfolder}")

"""    # --- Optional Visualization ---
    plt.figure(figsize=(8, 8))
    plt.imshow(dsm, cmap='gray', origin='upper')
    plt.title(f"DSM: {subfolder}")
    plt.colorbar(label="Height (m)")

    if street:
        x_min_local = -plane_width / 2
        y_max_local = plane_height / 2
        adjusted_street = []
        for x, y in street:
            px = (x - x_min_local) / cell_size
            py = (y_max_local - y) / cell_size
            adjusted_street.append((px - 0.5, py - 0.5))

        poly = Polygon(adjusted_street)
        if poly.is_valid:
            x_coords, y_coords = poly.exterior.xy
            plt.plot(x_coords, y_coords, color='red', linewidth=2, linestyle='--', label="Street")

    plt.axis('equal')
    plt.xlabel("X (pixels)")
    plt.ylabel("Y (pixels)")
    plt.legend()
    plt.tight_layout()
    plt.show()
"""
print("\n🎉 All folders processed successfully!")