import os
import json
import csv

# === Base directory and output file
base_dir = r"C:\Users\Ardo\Desktop\thesis\processed"
output_csv = os.path.join(base_dir, "street_attributes_summary.csv")

# === Define fields to include
fields = [
    "folder_name",
    "area",
    "width",
    "mean_building_height",
    "mean_building_height_side1",
    "mean_building_height_side2",
    "lh_ratio",
    "direction",
    "mrt_mean",
    "mrt_min",
    "mrt_max",
    "dir_sin",
    "dir_cos"
]

# === Prepare data list
rows = []

# === Walk through folders
for root, dirs, files in os.walk(base_dir):
    if "street_geo_with_mrt.json" in files:
        json_path = os.path.join(root, "street_geo_with_mrt.json")
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
                attrs = data.get("street_attributes", {})
                row = {key: attrs.get(key, None) for key in fields if key != "folder_name"}
                row["folder_name"] = os.path.basename(root)
                rows.append(row)
        except Exception as e:
            print(f"❌ Failed to process {json_path}:\n   {e}")

# === Write to CSV
with open(output_csv, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ Exported street attributes to CSV:\n{output_csv}")
