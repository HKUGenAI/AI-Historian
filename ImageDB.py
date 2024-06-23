import os
import csv
from openai import AzureOpenAI
import base64
from mimetypes import guess_type
from dotenv import load_dotenv

load_dotenv()

api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
deployment_name = 'trygpt4o'
api_version = '2024-02-01'  # this might change in the future

client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    base_url=f"{api_base}/openai/deployments/{deployment_name}"
)

# Function to encode a local image into data URL
def local_image_to_data_url(image_path):
    # Guess the MIME type of the image based on the file extension
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'  # Default MIME type if none is found

    # Read and encode the image file
    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')

    # Construct the data URL
    return f"data:{mime_type};base64,{base64_encoded_data}"

# Function to process images in a folder and write results to a CSV file
def process_images_in_folder(folder_path, output_file):
    with open(output_file, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['Image Name', 'Image Path', 'Response1', 'Response2'])

        for filename in os.listdir(folder_path):
            if filename.endswith('.jpg') or filename.endswith('.png'):
                image_path = os.path.join(folder_path, filename)
                data_url = local_image_to_data_url(image_path)

                systemMessage = '''You are a historian expert who can give information of a photo. 
Identify when the photo was taken, and recognize the objects and the events in the photo.
This is your task: List the keywords that help describe this photo, and group these keywords under 
0. Story: brieftly describe image
1. Objects:List all important object in the image
2. Events: List all important action, events in the image
3. Time: Estimate the time in that image (date/month/year)
in this order. Don't bold any text.
'''

                response = client.chat.completions.create(
                    model=deployment_name,
                    messages=[
                        {"role": "system", "content": systemMessage},
                        {"role": "user", "content": [
                            {
                                "type": "text",
                                "text": "Describe this picture:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url
                                }
                            }
                        ]}
                    ],
                    max_tokens=2000
                )

                response_text = response.choices[0].message.content
                response2_text = "\n".join(response_text.split("\n")[1:])  # Exclude the "Story" section

                csvwriter.writerow([filename, image_path, response_text, response2_text])

# Example usage
folder_path = 'imgfd'
output_file = 'output2.csv'
process_images_in_folder(folder_path, output_file)