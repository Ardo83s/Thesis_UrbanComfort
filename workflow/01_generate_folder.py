import json
import os
import math

# --- Configuration ---
input_folder = "C:/Users/Ardo/Desktop/thesis/data"      # Folder containing original JSONs
output_root = "C:/Users/Ardo/Desktop/thesis/processed"      # Root folder where subfolders will be created

width_bins = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
height_ranges = {
    5:  (5, 20), 
    10: (5, 20),
    15: (5, 20),
    20: (5, 24),
    25: (5, 26),
    30: (5, 28),
    35: (5, 28),
    40: (5, 28),
    45: (5, 28),
    50: (5, 30),
}

"""width_bins = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
height_ranges = {
    5:  (12, 20),
    10: (12, 20),
    15: (12, 20),
    20: (20, 24),
    25: (18, 26),
    30: (20, 28),
    35: (20, 28),
    40: (20, 28),
    45: (20, 28),
    50: (20, 30),
}"""

step_h = 5
hw_max = None  # Optional constraint on height/width ratio

# --- Utility functions ---
def round_up(x, step):
    return int(math.ceil(x / step) * step)

def generate_heights(w, hmin, hmax):
    h_start = round_up(hmin, step_h)
    heights = list(range(h_start, hmax + 1, step_h))
    if hw_max is not None:
        heights = [h for h in heights if (h / w) <= hw_max]
    return heights

# --- Ensure output root exists ---
if not os.path.exists(output_root):
    os.makedirs(output_root)

# --- Loop through all JSON files ---
all_files = [f for f in os.listdir(input_folder) if f.endswith(".json")]
total_generated = 0

for file in all_files:
    input_path = os.path.join(input_folder, file)

    with open(input_path, "r") as f:
        base_data = json.load(f)

    try:
        width = int(base_data["street_attributes"]["width"])
        rotation = int(base_data["rotation_degrees"])
        buildings = base_data["buildings"]
    except KeyError:
        print(f"⚠️ Skipping {file}: missing required fields.")
        continue

    if width not in height_ranges:
        print(f"⚠️ Skipping {file}: width {width} not in height_ranges.")
        continue

    hmin, hmax = height_ranges[width]
    height_vals = generate_heights(width, hmin, hmax)

    # All (min, max) height combinations
    height_combinations = []
    for i in range(len(height_vals)):
        for j in range(i, len(height_vals)):
            height_combinations.append((height_vals[i], height_vals[j]))

    # Process each height combination
    for min_h, max_h in height_combinations:
        new_data = base_data.copy()
        new_data["buildings"] = []

        for i, b in enumerate(buildings):
            h = min_h if i % 2 == 0 else max_h
            new_data["buildings"].append({
                "footprint": b["footprint"],
                "height": h
            })

        new_data["street_attributes"]["mean_building_height"] = (min_h + max_h) / 2.0
        new_data["street_attributes"]["mean_building_height_side1"] = min_h
        new_data["street_attributes"]["mean_building_height_side2"] = max_h
        new_data["street_attributes"]["lh_ratio"] = width / ((min_h + max_h) / 2.0)

        # Create output subfolder
        folder_name = f"width{width}_deg{rotation:03d}_h{min_h}to{max_h}"
        out_dir = os.path.join(output_root, folder_name)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        # Save JSON as street_geo.json
        out_path = os.path.join(out_dir, "street_geo.json")
        with open(out_path, "w") as out_file:
            json.dump(new_data, out_file, indent=2)

        total_generated += 1

print(f"✅ Done. {total_generated} JSON files created in '{output_root}'.")
