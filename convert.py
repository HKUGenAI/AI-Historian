import os
from PIL import Image
from io import BytesIO

# Set the input and output folders
input_folder = 'tif'
output_folder = 'jpg'

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Iterate through the files in the input folder
for filename in os.listdir(input_folder):
    if filename.endswith('.tif'):
        # Open the image
        img_path = os.path.join(input_folder, filename)
        img = Image.open(img_path)

        # Resize the image to be less than 15 MB
        img.thumbnail((1920, 1080))
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG', optimize=True, quality=80)
        img_size = img_bytes.getbuffer().nbytes

        while img_size > 15 * 1024 * 1024:
            img.thumbnail((img.width // 2, img.height // 2))
            img_bytes = BytesIO()
            img.save(img_bytes, format='JPEG', optimize=True, quality=80)
            img_size = img_bytes.getbuffer().nbytes

        # Save the resized image to the output folder
        output_filename = os.path.splitext(filename)[0] + '.jpg'
        output_path = os.path.join(output_folder, output_filename)
        img.save(output_path, 'JPEG')
        print(f'Converted {filename} to {output_filename}')