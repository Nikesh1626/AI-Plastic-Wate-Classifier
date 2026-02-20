import os

# Path to dataset folder
DATASET_PATH = "plastic-ai-project/dataset"
# Allowed image extensions
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

print("📊 Image count per class:\n")

total_images = 0

for folder in os.listdir(DATASET_PATH):
    folder_path = os.path.join(DATASET_PATH, folder)

    if os.path.isdir(folder_path):
        count = sum(
            1 for file in os.listdir(folder_path)
            if file.lower().endswith(IMAGE_EXTENSIONS)
        )
        total_images += count
        print(f"{folder}: {count} images")

print("\n✅ Total images in dataset:", total_images)