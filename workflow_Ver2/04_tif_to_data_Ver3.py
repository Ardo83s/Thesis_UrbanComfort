import os
import json
import rasterio
import math
import numpy as np
from shapely.geometry import shape
from rasterio.features import geometry_mask

# === BASE DIRECTORY TO WALK
base_dir = r"C:\Users\Ardo\Desktop\thesis\processed"

# === Helper function to process each folder
def process_files(geojson_path, tif_path, rotated_json_path):
    output_json_path = rotated_json_path.replace(".json", "_with_mrt.json")

    # 1. Load georeferenced GeoJSON
    with open(geojson_path) as f:
        geo = json.load(f)

    # 2. Extract street geometry
    street_geom = None
    for feature in geo["features"]:
        if feature["properties"].get("type") == "street":
            street_geom = shape(feature["geometry"])
            break

    if not street_geom:
        print(f"❌ No street geometry found in {geojson_path}")
        return

    # 3. Load MRT raster and mask with street geometry
    with rasterio.open(tif_path) as src:
        raster = src.read(1)
        transform = src.transform
        mask = geometry_mask([street_geom], transform=transform, invert=True, out_shape=raster.shape)
        masked = np.where(mask, raster, np.nan)

        mrt_mean = float(np.nanmean(masked))
        mrt_min = float(np.nanmin(masked))
        mrt_max = float(np.nanmax(masked))

    # 4. Load rotated JSON (street_geo.json)
    with open(rotated_json_path) as f:
        rotated = json.load(f)

    if "street_attributes" not in rotated:
        rotated["street_attributes"] = {}

    # 5. Add MRT values
    rotated["street_attributes"]["mrt_mean"] = round(mrt_mean, 2)
    rotated["street_attributes"]["mrt_min"] = round(mrt_min, 2)
    rotated["street_attributes"]["mrt_max"] = round(mrt_max, 2)

    # 6. Add direction sin/cos encoding
    direction_deg = rotated["street_attributes"].get("direction", 0)
    direction_rad = math.radians(direction_deg)
    rotated["street_attributes"]["dir_sin"] = math.sin(direction_rad)
    rotated["street_attributes"]["dir_cos"] = math.cos(direction_rad)

    # 7. Save updated JSON
    with open(output_json_path, "w") as f:
        json.dump(rotated, f, indent=2)

    print(f"✅ Processed:\n{output_json_path}")
    print(f"  mrt_mean: {mrt_mean:.2f}")
    print(f"  mrt_min : {mrt_min:.2f}")
    print(f"  mrt_max : {mrt_max:.2f}")
    print(f"  dir_sin : {rotated['street_attributes']['dir_sin']:.4f}")
    print(f"  dir_cos : {rotated['street_attributes']['dir_cos']:.4f}")

# === Walk through all folders
for root, dirs, files in os.walk(base_dir):
    geojson_path = os.path.join(root, "total.geojson")
    rotated_json_path = os.path.join(root, "street_geo.json")
    tif_path = os.path.join(root, "Tmrt_average.tif")

    # Process only if all required files exist
    if os.path.exists(geojson_path) and os.path.exists(rotated_json_path) and os.path.exists(tif_path):
        try:
            process_files(geojson_path, tif_path, rotated_json_path)
        except Exception as e:
            print(f"❌ Error processing in {root}:\n   {e}")
    else:
        print(f"⚠️ Skipped folder (missing required files): {root}")
