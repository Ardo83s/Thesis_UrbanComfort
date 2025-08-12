import json
import rasterio
from shapely.geometry import shape, Polygon
from rasterio.features import geometry_mask
import numpy as np
import math

# === FILE PATHS
geojson_path = r"C:\Users\Andrea\Desktop\thesis\rotated_json\geojson_export\dsm_045deg_full.geojson"
tif_path = r"C:\Users\Andrea\Desktop\thesis\rotated_json\mrt_045deg\Tmrt_average.tif"
rotated_json_path = r"C:\Users\Andrea\Desktop\thesis\rotated_json\dsm_045deg.json"
output_json_path = rotated_json_path.replace(".json", "_with_mrt.json")

# === 1. Load georeferenced GeoJSON
with open(geojson_path) as f:
    geo = json.load(f)

# === 2. Extract street geometry
street_geom = None
for feature in geo["features"]:
    if feature["properties"].get("type") == "street":
        street_geom = shape(feature["geometry"])
        break

if not street_geom:
    raise Exception("❌ No street geometry found in the georeferenced GeoJSON.")

# === 3. Load MRT raster and mask with street geometry
with rasterio.open(tif_path) as src:
    raster = src.read(1)
    transform = src.transform
    mask = geometry_mask([street_geom], transform=transform, invert=True, out_shape=raster.shape)
    masked = np.where(mask, raster, np.nan)

    mrt_mean = float(np.nanmean(masked))
    mrt_min = float(np.nanmin(masked))
    mrt_max = float(np.nanmax(masked))

# === 4. Load rotated JSON (local coordinates)
with open(rotated_json_path) as f:
    rotated = json.load(f)

if "street_attributes" not in rotated:
    rotated["street_attributes"] = {}

# === 5. Add MRT values
rotated["street_attributes"]["mrt_mean"] = mrt_mean
rotated["street_attributes"]["mrt_min"] = mrt_min
rotated["street_attributes"]["mrt_max"] = mrt_max

# === 6. Add direction sin/cos encoding
direction_deg = rotated["street_attributes"].get("direction", 0)
direction_rad = math.radians(direction_deg)
rotated["street_attributes"]["dir_sin"] = math.sin(direction_rad)
rotated["street_attributes"]["dir_cos"] = math.cos(direction_rad)

# === 7. Save updated JSON
with open(output_json_path, "w") as f:
    json.dump(rotated, f, indent=2)

print(f"✅ MRT and direction values added to:\n{output_json_path}")
print(f"  mrt_mean: {mrt_mean:.2f}")
print(f"  mrt_min : {mrt_min:.2f}")
print(f"  mrt_max : {mrt_max:.2f}")
print(f"  dir_sin : {rotated['street_attributes']['dir_sin']:.4f}")
print(f"  dir_cos : {rotated['street_attributes']['dir_cos']:.4f}")
