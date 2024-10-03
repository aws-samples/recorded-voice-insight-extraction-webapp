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
from components.bedrock_utils import LLM, tmp_retrieve_and_generate
from components.db_utils import (
    retrieve_all_items,
    retrieve_analysis_by_jobid,
    store_analysis_result,
)
from components.s3_utils import retrieve_transcript_by_jobid
from components.cognito_utils import login
from components.streamlit_utils import display_sidebar

st.set_page_config(
    page_title="test",
    page_icon=":brain:",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("test kb")
# if not st.session_state.get("auth_username", None):
#     st.error("Please login to continue.")
#     login()
#     st.stop()
st.subheader("Pick a media file to analyze:")
display_sidebar()


@st.cache_resource
def get_LLM():
    return LLM()


llm = get_LLM()
username = "demouser"
job_df = retrieve_all_items(username=username)
completed_jobs = job_df[job_df.job_status == "Indexing"]  # TODO

selected_media_name = st.selectbox(
    "dummy_label",
    options=completed_jobs.media_name.to_list() + ["CHAT WITH ALL OF THEM!"],
    index=None,
    placeholder="Select a media file to analyze",
    label_visibility="collapsed",
)
if selected_media_name == "CHAT WITH ALL OF THEM!":
    selected_media_name = None

if user_message := st.chat_input(placeholder="Enter your question here"):
    with st.chat_message("user"):
        st.write(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            llm_response = tmp_retrieve_and_generate(
                query=user_message, username=username, media_name=selected_media_name
            )

        st.write(llm_response)
