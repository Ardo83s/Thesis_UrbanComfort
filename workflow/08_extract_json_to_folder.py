import os
import shutil

# Define paths
source_root = r"C:\Users\Ardo\Desktop\thesis\processed"
destination_root = r"C:\Users\Ardo\Desktop\thesis\post_processed"
target_filename = "street_geo_with_mrt.json"

# Create destination folder if it doesn't exist
os.makedirs(destination_root, exist_ok=True)

# Loop through all items in the source directory
for folder_name in os.listdir(source_root):
    folder_path = os.path.join(source_root, folder_name)
    
    # Only process directories
    if os.path.isdir(folder_path):
        source_file = os.path.join(folder_path, target_filename)
        
        if os.path.isfile(source_file):
            destination_file = os.path.join(destination_root, f"{folder_name}.json")
            shutil.copy2(source_file, destination_file)
            print(f"Copied: {source_file} -> {destination_file}")
        else:
            print(f"File not found in {folder_path}: {target_filename}")
