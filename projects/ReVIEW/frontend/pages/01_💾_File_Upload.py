import os

import boto3
import streamlit as st

# Must match what's in the backend stack definition
BUCKET_NAME = "review-app-assets"


st.set_page_config(
    page_title="File Upload",
    page_icon=":floppy_disk:",
    layout="centered",
    initial_sidebar_state="expanded",
)


def uploadToS3(fileobj):
    s3 = boto3.client("s3")

    try:
        s3.upload_fileobj(
            fileobj,
            BUCKET_NAME,
            os.path.join("recordings", os.path.split(fileobj.name)[-1]),
        )
        st.success(
            f"{fileobj.name} successfully uploaded and submitted for transcription."
        )
        return True
    except FileNotFoundError:
        st.error(f"File {fileobj.name} not found.")
        return False


st.title("File Uploader")

uploaded_file = st.file_uploader("Upload a video or audio recording.")
if uploaded_file is not None:
    st.info(f"Uploading file {uploaded_file.name}...")
    uploadToS3(uploaded_file)
