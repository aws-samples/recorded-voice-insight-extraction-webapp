import streamlit as st
from components.cognito_utils import login
from components.streamlit_utils import display_sidebar
from components.s3_utils import uploadToS3
from components.io_utils import check_valid_file_extension

st.set_page_config(
    page_title="File Upload",
    page_icon=":floppy_disk:",
    layout="centered",
    initial_sidebar_state="expanded",
)


st.title("File Uploader")

if not st.session_state.get("auth_username", None):
    st.error("Please login to continue.")
    login()
    st.stop()

display_sidebar()

uploaded_file = st.file_uploader("Upload a video or audio recording.")
if uploaded_file is not None:
    if not check_valid_file_extension(uploaded_file.name):
        st.error(
            'Invalid file extension. Allowed extensions are: "mp3", "mp4", "wav", "flac", "ogg", "amr", "webm", "m4a".'
        )
        st.stop()

    st.info(f"Uploading file {uploaded_file.name}...")
    upload_successful = uploadToS3(
        uploaded_file, username=st.session_state["auth_username"]
    )
    if upload_successful:
        st.success(
            f"{uploaded_file.name} successfully uploaded and submitted for transcription. Check its progress on the Job Status page."
        )
    else:
        st.error(f"File {uploaded_file.name} not found.")
