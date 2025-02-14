import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import *
from azure.search.documents.models import VectorizedQuery
import openai
from openai import AzureOpenAI
import re
from setup import text_search_client, image_search_client, azure_openai_client, get_embedding
from filter_images import filter_images

# Set the page layout to wide
st.set_page_config(page_title="AIHA", page_icon="🔎", layout="wide")

# Set the title of the Streamlit app
st.title("AI Historian Assistant")

systemMessage = """You are a friendly and informative AI Historian that helps user to answer questions from sources provided. Be specific in your answers.
                    Answer ONLY with the facts listed in the list of sources below. If the question is not related to the sources, politely decline. 
                    After anwering the user quesitons, start a new line and give 3 keywords (names, places, etc.) of your response. Do NOT give keywords "HKU", "The University of Hong Kong", "Hong Kong".
                    If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below.
                    Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. 
                    Use square brackets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
                    NEVER give out the original source text without paraphrasing.
                """
history_init = [
    {'role' : 'user', 'content' : ""},
    {'role' : 'system', 'content' : systemMessage}
]

# Initialize session state for chat history if not already present
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Initialize session state for OpenAI chat history if not already present
if "history_openai" not in st.session_state:
    st.session_state["history_openai"] = history_init

# Function to handle user queries and generate responses
def query_and_respond(query):
    vector_query = get_embedding(query)

    # Perform text search using vector-based queries
    text_results = text_search_client.search(
        search_text=None,
        top=5,
        vector_queries=[VectorizedQuery(vector=vector_query, fields="Embedding")],
    )
    # Perform neighboring search
    sections = []
    for result in text_results:
        sections.append(result["id"])
    print(sections)
    search_text_results = []
    used_sections = []
    for sec in sections:
        doc = text_search_client.get_document(key=sec)
        if doc["id"] == "Chapter-Section-Paragraph": continue
        print(doc["id"])
        used_sections.append(doc["id"])
        search_text_results.append("Source: " + doc["id"] + "; Content: " + doc["Content"])
        try:
            neighbor_sec = sec[:-2] + "-" + str(int(sec[-1]) + 1)
            if neighbor_sec not in used_sections:
                doc = text_search_client.get_document(key=neighbor_sec)
                print(doc["id"])
                used_sections.append(doc["id"])
                search_text_results.append("Source: " + doc["id"] + "; Content: " + doc["Content"])
        except:
            pass
        try:
            neighbor_sec = sec[:-2] + "-" + str(int(sec[-1]) - 1)
            if neighbor_sec not in used_sections:
                doc = text_search_client.get_document(key=neighbor_sec)
                print(doc["id"])
                used_sections.append(doc["id"])
                search_text_results.append("Source: " + doc["id"] + "; Content: " + doc["Content"])
        except:
            pass
    # Update conversation history for AI response
    chat_message = f"{query} Source: " + " ".join(search_text_results)
    history_openai = st.session_state["history_openai"]
    history_openai.append({"role": "user", "content": chat_message})

    # Generate AI response using chat completions
    response = azure_openai_client.chat.completions.create(
        model="summer",
        messages=history_openai,
        temperature=0.7,
    )
    history_openai.append(
        {"role": "assistant", "content": response.choices[0].message.content}
    )
    st.session_state["history_openai"] = history_openai

    # Perform image search using vector-based KEYWORDS
    chat_content = response.choices[0].message.content
    image_search_keywords = chat_content.split("\n")[-1].replace("Keywords: ", "")
    print(image_search_keywords)
    image_results = image_search_client.search(
        search_text=None,
        top=5,
        vector_queries=[VectorizedQuery(vector=get_embedding(image_search_keywords), fields="Embedding")],
    )
    image_search_results = [(result["Image_name"], result["Caption"]) for result in image_results]
    filtered_image_names = filter_images(azure_openai_client, chat_content, image_search_results)
    filtered_images = []
    for i in image_search_results:
        if i[0] in filtered_image_names:
            filtered_images.append(i)
    return (
        response.choices[0].message.content,
        search_text_results,
        filtered_images,
    )

# Display the text bubbles with the chat history
def show_chat_history():
    for chat in st.session_state["chat_history"]:
        if chat["user"] == "AI": h = 300
        elif chat["user"] == "You": h = 100
        st.text_area(
            f"{chat['user']}:",
            height=h,
            value=chat["message"],
            key=chat["user"] + chat["message"],
        )

def filename_converter(filename):
    # Remove the file extension
    name_without_extension = os.path.splitext(filename)[0]
    # Remove leading numbers/special characters and replace underscores/hyphens with spaces
    name_cleaned = ''.join([char if char.isalnum() else ' ' for char in name_without_extension if not char.isdigit()])
    name_cleaned = name_cleaned.replace('_', ' ').replace('-', ' ').strip()
    # Capitalize the first letter of each word
    image_title = ' '.join(word.capitalize() for word in name_cleaned.split())
    return image_title

# User interface for chat interaction
user_input = st.chat_input("Type your message here:")
if user_input:
    st.session_state["chat_history"].append({"user": "You", "message": user_input})
    # Show chat history so far
    show_chat_history()
    ai_response, search_results, image_result = query_and_respond(user_input)
    st.session_state["chat_history"].append({"user": "AI", "message": ai_response})
    # Show AI response
    st.text_area("AI:", value=ai_response, height=300, key="AI"+ai_response)
    
    if image_result != ['']:
        # Extract and display images from the search results
        with st.sidebar:
            st.subheader("Image Results")
            for i in range(len(image_result)):
                if image_result[i][1] == 'None': caption = filename_converter(image_result[i][0])
                else: caption = image_result[i][1]
                st.image("./jpg/" + str(image_result[i][0]), caption=caption)