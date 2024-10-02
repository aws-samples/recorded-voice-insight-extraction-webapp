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
from components.bedrock_utils import LLM, chat_transcript_query
from components.db_utils import (
    retrieve_all_items,
)
from components.parsing_utils import extract_timestamp_and_answer
from components.s3_utils import retrieve_media_bytes, retrieve_transcript_json_by_jobid
from components.transcripts_utils import build_timestamped_segmented_transcript
from components.cognito_utils import login
from components.streamlit_utils import display_sidebar

st.set_page_config(
    page_title="Chat With Your Media",
    page_icon=":speech_balloon:",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("Chat with Your Media")
if not st.session_state.get("auth_username", None):
    st.error("Please login to continue.")
    login()
    st.stop()
st.subheader("Pick a media file to chat with:")
display_sidebar()


@st.cache_resource
def get_LLM():
    return LLM()


llm = get_LLM()

job_df = retrieve_all_items(username=st.session_state["auth_username"])
completed_jobs = job_df[job_df.job_status == "Completed"]

selected_media_name = st.selectbox(
    "dummy_label",
    options=completed_jobs.media_name,
    index=None,
    placeholder="Select a media file to chat with",
    label_visibility="collapsed",
)

if selected_media_name:
    media_bytes = retrieve_media_bytes(
        selected_media_name, username=st.session_state["auth_username"]
    )

    if user_message := st.chat_input(placeholder="Enter your question here"):
        with st.chat_message("user"):
            st.write(user_message)
        selected_job_id = job_df[job_df.media_name == selected_media_name][
            "UUID"
        ].values[0]
        transcript_json = retrieve_transcript_json_by_jobid(
            job_id=selected_job_id, username=st.session_state["auth_username"]
        )
        segmented_transcript_str = build_timestamped_segmented_transcript(
            transcript_json
        )

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                llm_response = chat_transcript_query(
                    segmented_transcript=segmented_transcript_str,
                    user_query=user_message,
                    llm=llm,
                )

                answer, timestamp_int = extract_timestamp_and_answer(llm_response)
            if timestamp_int >= 0:
                # Note: this works for audio files, too.
                video = st.video(
                    data=media_bytes,
                    start_time=timestamp_int,
                )
            st.write(answer)
