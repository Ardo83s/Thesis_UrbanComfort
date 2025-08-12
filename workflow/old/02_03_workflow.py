import os
import sys
import json
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import Polygon

# === CONFIGURATION ===

QGIS_PATH = r"C:\Program Files\QGIS 3.34.12"
input_root = r"C:\Users\Ardo\Desktop\thesis\processed"
utm_x_origin = 430000
utm_y_origin = 4580000
CRS = "EPSG:25831"

# === ENVIRONMENT SETUP ===

os.environ['QGIS_PREFIX_PATH'] = os.path.join(QGIS_PATH, 'apps', 'qgis-ltr')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(QGIS_PATH, 'apps', 'Qt5', 'plugins', 'platforms')
os.environ['GDAL_DATA'] = os.path.join(QGIS_PATH, 'share', 'gdal')

dll_paths = [
    os.path.join(QGIS_PATH, 'bin'),
    os.path.join(QGIS_PATH, 'apps', 'qgis-ltr', 'bin'),
    os.path.join(QGIS_PATH, 'apps', 'Qt5', 'bin')
]
os.environ['PATH'] = ';'.join(dll_paths + os.environ['PATH'].split(';'))

sys.path.append(os.path.join(QGIS_PATH, 'apps', 'qgis-ltr', 'python'))
sys.path.append(os.path.join(QGIS_PATH, 'apps', 'qgis-ltr', 'python', 'plugins'))
sys.path.append(os.path.join(QGIS_PATH, 'apps', 'Python312', 'Lib', 'site-packages'))
sys.path.append(os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming', 'QGIS', 'QGIS3', 'profiles', 'default', 'python', 'plugins'))

# === QGIS INIT ===

from qgis.core import QgsApplication
from processing.core.Processing import Processing
from processing_umep.processing_umep_provider import ProcessingUMEPProvider
import processing

QgsApplication.setPrefixPath(os.environ['QGIS_PREFIX_PATH'], True)
qgs = QgsApplication([], False)
qgs.initQgis()

Processing.initialize()
QgsApplication.processingRegistry().addProvider(ProcessingUMEPProvider())

print("✅ QGIS initialized successfully with UMEP")

# === MAIN LOOP ===

for subfolder in os.listdir(input_root):
    folder_path = os.path.join(input_root, subfolder)
    json_path = os.path.join(folder_path, "street_geo.json")

    if not os.path.isdir(folder_path) or not os.path.exists(json_path):
        continue

    print(f"\n📂 Processing: {subfolder}")

    with open(json_path, "r") as f:
        data = json.load(f)

    cell_size = data["cell_size"]
    plane_width, plane_height = data["plane_size"]
    buildings = data["buildings"]

    cols = int(np.ceil(plane_width / cell_size))
    rows = int(np.ceil(plane_height / cell_size))

    local_transform = from_origin(-plane_width / 2, plane_height / 2, cell_size, cell_size)
    world_x_top_left = utm_x_origin - plane_width / 2
    world_y_top_left = utm_y_origin + plane_height / 2
    world_transform = from_origin(world_x_top_left, world_y_top_left, cell_size, cell_size)

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

    dsm_path = os.path.join(folder_path, "dsm.tif")
    with rasterio.open(
        dsm_path, "w", driver="GTiff", height=rows, width=cols,
        count=1, dtype=dsm.dtype, crs=CRS, transform=world_transform
    ) as dst:
        dst.write(dsm, 1)

    # Flat zero DEM
    dem = np.zeros_like(dsm, dtype=np.float32)
    dem_path = os.path.join(folder_path, "dem.tif")
    with rasterio.open(
        dem_path, "w", driver="GTiff", height=rows, width=cols,
        count=1, dtype=dem.dtype, crs=CRS, transform=world_transform
    ) as dst:
        dst.write(dem, 1)

    print("✅ DSM and DEM saved")

    # === Run UMEP Sky View Factor ===

    svf_path = os.path.join(folder_path, "svf.tif")
    try:
        result = processing.run("umep:Urban Geometry: Sky View Factor", {
            'INPUT_DSM': dsm_path,
            'INPUT_CDSM': None,
            'TRANS_VEG': 3,
            'INPUT_TDSM': None,
            'INPUT_THEIGHT': 25,
            'ANISO': True,
            'WALL_SCHEME': False,
            'KMEANS': True,
            'CLUSTERS': 5,
            'INPUT_DEM': dem_path,
            'INPUT_SVFHEIGHT': 1,
            'OUTPUT_DIR': folder_path,
            'OUTPUT_FILE': svf_path
        })
        print(f"✅ SVF created: {svf_path}")

    except Exception as e:
        print(f"❌ SVF processing failed in {subfolder}: {e}")

# === Cleanup ===
qgs.exitQgis()
print("\n🚪 QGIS session closed. All done.")
