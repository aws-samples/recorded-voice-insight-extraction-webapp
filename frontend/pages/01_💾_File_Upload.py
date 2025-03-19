# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import streamlit as st
from components.cognito_utils import login
from components.streamlit_utils import display_sidebar, show_cover
from components.s3_utils import upload_to_s3
from components.io_utils import check_valid_file_extension
import urllib.parse

st.set_page_config(
    page_title="File Upload",
    page_icon=":floppy_disk:",
    layout="centered",
    initial_sidebar_state="expanded",
)

show_cover(title="ReVIEW", description="Upload a video or audio recording")

if not st.session_state.get("auth_username", None):
    st.error("Please login to continue.")
    login()
    st.stop()

username = st.session_state["auth_username"]
api_auth_id_token = st.session_state["auth_id_token"]

display_sidebar()

uploaded_file = st.file_uploader("File Uploader", label_visibility="hidden")
if uploaded_file is not None:
    if not check_valid_file_extension(uploaded_file.name):
        st.error(
            'Invalid file extension. Allowed extensions are: "mp3", "mp4", "wav", "flac", "ogg", "amr", "webm", "m4a".'
        )
        st.stop()
    url_encoded_filename = urllib.parse.quote_plus(uploaded_file.name)
    if url_encoded_filename != uploaded_file.name:
        st.warning(f"Renaming file to {url_encoded_filename}...")
    st.info(f"Uploading file {url_encoded_filename}...")
    upload_successful = upload_to_s3(
        uploaded_file,
        filename=url_encoded_filename,
        username=username,
        api_auth_id_token=api_auth_id_token,
    )
    if upload_successful:
        st.success(
            f"{url_encoded_filename} successfully uploaded and submitted for transcription. Check its progress on the Job Status page."
        )
    else:
        st.error(f"File {uploaded_file.name} not found.")
