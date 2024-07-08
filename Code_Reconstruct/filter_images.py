from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import *
from azure.search.documents.models import VectorizedQuery
import openai
from openai import AzureOpenAI

def filter_images(openai_client, text, image_list):
    prompt = """Below is a section of text, followed by a list of images. 
                If the text is not a historical answer, i.e. a description or explanation of historical events or people, return an empty string.
                Otherwise, based on the image titles and captions, if the image title or caption cannot be found in the text, remove it from the list.
                For instance, if the name 'James Cantlie' cannot be found in the text, remove 'Sir James Cantlie.jpg' from the image list.
                Return only the filenames of the remaining, unremoved images, each separated by a newline.
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
