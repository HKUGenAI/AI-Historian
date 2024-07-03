from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import *
from azure.search.documents.models import VectorizedQuery
import openai
from openai import AzureOpenAI

def filter_images(openai_client, text, image_list):
    prompt = """Below is a section of text, followed by a list of images. 
                If the text is not a historical answer, i.e. a description or explanation of historical events or people, return an empty string.
                Otherwise, based on the image titles and captions, filter and remove any images with titles, captions, or content that 
                cannot be found or are not included in the text.
                For instance, if the text does not explicitly include the name 'James Cantlie', remove 'Sir James Cantlie.jpg' from the image list.
                Remove as many images as possible. 
                Return only the filenames of the images, each separated by a newline.
             """
    history = [
        {'role' : 'user', 'content' : ""},
        {'role' : 'system', 'content' : prompt + text + "".join(image_list)}
    ]   

    response = openai_client.chat.completions.create(
        model="summer",
        messages=history,
        temperature=0.7,
    )

    return response.choices[0].message.content.split("\n")
