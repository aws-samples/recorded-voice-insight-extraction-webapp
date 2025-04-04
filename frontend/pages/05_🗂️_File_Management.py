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
from components.db_utils import retrieve_all_items
from components.s3_utils import delete_file_by_jobid

st.set_page_config(
    page_title="File Management",
    page_icon="	:card_index_dividers:",
    layout="centered",
    initial_sidebar_state="expanded",
)

show_cover(title="ReVIEW", description="Manage uploaded Files")

if not st.session_state.get("auth_username", None):
    st.error("Please login to continue.")
    login()
    st.stop()

username = st.session_state["auth_username"]
api_auth_id_token = st.session_state["auth_id_token"]

display_sidebar()

job_df = retrieve_all_items(
    username=username, max_rows=None, api_auth_id_token=api_auth_id_token
)

st.subheader("Choose files to delete:")
media_names_to_delete = st.multiselect(  # This is an empty list if nothing is selected
    "kazu",
    options=sorted(job_df.media_name.to_list()),  # Display alphabetically
    placeholder="Select file(s) to permanently delete",
    label_visibility="collapsed",
)

button_pressed = st.button(
    label="Delete Permanently",
    key="foo",
)

if button_pressed and media_names_to_delete:
    for media_name_to_delete in media_names_to_delete:
        job_id = job_df[job_df.media_name == media_name_to_delete]["UUID"].values[0]
        st.info(f"Deleting {media_name_to_delete}...")
        deletion_response = delete_file_by_jobid(
            job_id=job_id, username=username, api_auth_id_token=api_auth_id_token
        )
    st.success("File deletion complete.")
