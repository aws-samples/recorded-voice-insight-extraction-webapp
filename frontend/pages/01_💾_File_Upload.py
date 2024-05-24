import os

import boto3
import streamlit as st
from components.cognito_utils import login

# Must match what's in the backend stack definition
BUCKET_NAME = "review-app-assets"


st.set_page_config(
    page_title="File Upload",
    page_icon=":floppy_disk:",
    layout="centered",
    initial_sidebar_state="expanded",
)


def uploadToS3(fileobj, username):
    s3 = boto3.client("s3")

    try:
        s3.upload_fileobj(
            fileobj,
            BUCKET_NAME,
            os.path.join("recordings", username, os.path.split(fileobj.name)[-1]),
        )
        st.success(
            f"{fileobj.name} successfully uploaded and submitted for transcription."
        )
        return True
    except FileNotFoundError:
        st.error(f"File {fileobj.name} not found.")
        return False


st.title("File Uploader")

if not st.session_state.get("auth_username", None):
    st.error("Please login to continue.")
    login()
    st.stop()

else:
    uploaded_file = st.file_uploader("Upload a video or audio recording.")
    if uploaded_file is not None:
        st.info(f"Uploading file {uploaded_file.name}...")
        uploadToS3(uploaded_file, username=st.session_state["username"])
