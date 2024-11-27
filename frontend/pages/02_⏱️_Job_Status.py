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
from components.db_utils import retrieve_all_items
from components.cognito_utils import login
from components.streamlit_utils import display_sidebar, show_cover

st.set_page_config(
    page_title="Job Status",
    page_icon=":stopwatch:",
    layout="centered",
    initial_sidebar_state="expanded",
)

show_cover(title="ReVIEW", description="Check Transcription Job Status")

if not st.session_state.get("auth_username", None):
    st.error("Please login to continue.")
    login()
    st.stop()
display_sidebar()


username = st.session_state["auth_username"]
api_auth_token = st.session_state["auth_id_token"]
st.write("\n\n")
st.dataframe(
    retrieve_all_items(username=username, max_rows=None, api_auth_token=api_auth_token),
    hide_index=True,
    column_order=("media_name", "job_creation_time", "job_status"),
)

button_clicked = st.button("Refresh Table")
if button_clicked:
    # Refresh entire page on button click, just to reload the table
    st.rerun()
