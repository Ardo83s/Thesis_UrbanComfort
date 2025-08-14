import os
import rasterio
import numpy as np
import csv

base_dir = r"C:\Users\Ardo\Desktop\thesis\processed"
output_dir = os.path.join(base_dir, "exported_grids")
os.makedirs(output_dir, exist_ok=True)

for root, dirs, files in os.walk(base_dir):
    tif_path = os.path.join(root, "Tmrt_average.tif")
    
    if os.path.exists(tif_path):
        folder_name = os.path.basename(root)
        output_csv = os.path.join(output_dir, f"{folder_name}_Tmrt_grid.csv")

        with rasterio.open(tif_path) as src:
            data = src.read(1)
            transform = src.transform

            with open(output_csv, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["x", "y", "value"])

                for row in range(data.shape[0]):
                    for col in range(data.shape[1]):
                        value = data[row, col]
                        if np.isnan(value):
                            continue
                        x, y = transform * (col, row)
                        writer.writerow([x, y, round(float(value), 2)])

        print(f"✅ Exported: {output_csv}")
