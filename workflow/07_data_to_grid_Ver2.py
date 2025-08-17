import os
import rasterio
import numpy as np
import csv

# === Configuration
base_dir = r"C:\Users\Ardo\Desktop\thesis\processed"
output_dir = os.path.join(base_dir, "exported_grids_local")
os.makedirs(output_dir, exist_ok=True)

for root, dirs, files in os.walk(base_dir):
    tif_path = os.path.join(root, "Tmrt_average.tif")

    if os.path.exists(tif_path):
        folder_name = os.path.basename(root)
        output_csv = os.path.join(output_dir, f"{folder_name}_Tmrt_local.csv")

        with rasterio.open(tif_path) as src:
            data = src.read(1)
            height, width = data.shape

            # Expected: width = height = 150
            cell_size = 1.0  # meter
            x_min = -width / 2 * cell_size + cell_size / 2  # center at 0
            y_max = height / 2 * cell_size - cell_size / 2  # center at 0

            with open(output_csv, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["x", "y", "value"])

                for row in range(height):
                    for col in range(width):
                        value = data[row, col]
                        if np.isnan(value):
                            continue

                        # Compute local x, y centered at (0,0)
                        x = x_min + col * cell_size
                        y = y_max - row * cell_size  # because row 0 is top
                        writer.writerow([round(x, 2), round(y, 2), round(float(value), 2)])

        print(f"✅ Exported local grid: {output_csv}")
