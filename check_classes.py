from tensorflow.keras.preprocessing.image import ImageDataGenerator

datagen = ImageDataGenerator()
gen = datagen.flow_from_directory(
    "plastic-ai-project/dataset",
    target_size=(224, 224),
    batch_size=1
)

print(gen.class_indices)