import os

folders = [
    "plastic-ai-project/dataset",
    "plastic-ai-project/model",
    "plastic-ai-project/static/css",
    "plastic-ai-project/static/js",
    "plastic-ai-project/templates"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)

print("✅ Project folder structure created successfully!")