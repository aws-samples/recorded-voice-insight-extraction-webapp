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
from components.bedrock_utils import (
    generate_answer_no_chunking,
    retrieve_and_generate_answer,
)
from components.cognito_utils import login
from components.db_utils import retrieve_all_items
from components.s3_utils import retrieve_media_url, retrieve_transcript_by_jobid
from components.streamlit_utils import (
    display_sidebar,
    display_video_at_timestamp,
    draw_or_redraw_citation_buttons,
    reset_citation_session_state,
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []


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

username = st.session_state["auth_username"]
api_auth_token = st.session_state["auth_id_token"]

st.subheader("Pick media file to analyze:")
display_sidebar()

job_df = retrieve_all_items(
    username=username, max_rows=None, api_auth_token=api_auth_token
)
completed_jobs = job_df[job_df.job_status == "Completed"]

CHAT_WITH_ALL_STRING = "Chat with all media files"
selected_media_name = st.selectbox(
    "dummy_label",
    options=[CHAT_WITH_ALL_STRING] + completed_jobs.media_name.to_list(),
    index=None,
    placeholder="Select a media file to analyze",
    label_visibility="collapsed",
)
if selected_media_name == CHAT_WITH_ALL_STRING:
    selected_media_name = None


# Display chat messages from history on app rerun
# Only display the last two for better user experience
# (since this isn't really a stateful chat)
# If the last message is an assistant message, display in a special way
for message in st.session_state.messages[-2:-1]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# If page is reloading and any buttons are visible
if st.session_state.get("n_buttons", 0):
    # Check if any buttons are pressed
    for k, v in st.session_state.items():
        # If this button is pressed, show video
        if k.startswith("citation_button_") and v:
            clicked_citation_index = int(k.split("_")[-1])
            clicked_citation_media = st.session_state[
                f"citation_media_{clicked_citation_index}"
            ]
            clicked_citation_timestamp = st.session_state[
                f"citation_timestamp_{clicked_citation_index}"
            ]
            # Display the appropriate video
            clicked_media_url = retrieve_media_url(
                clicked_citation_media, username=username, api_auth_token=api_auth_token
            )

            display_video_at_timestamp(clicked_media_url, clicked_citation_timestamp)
            # Redraw the buttons
            draw_or_redraw_citation_buttons()

            # Display the assistant response
            assistant_message = st.session_state.messages[-1]
            with st.chat_message(assistant_message["role"]):
                st.markdown(assistant_message["content"])

# If the user has just typed a new message
if user_message := st.chat_input(placeholder="Enter your question here"):
    # Clear all info about previous questions, citations, etc
    reset_citation_session_state()
    # Display user message in chat message container
    with st.chat_message("user"):
        st.write(user_message)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_message})
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # If no specific media file is selected, use RAG over all files
            if not selected_media_name:
                full_answer = retrieve_and_generate_answer(
                    query=user_message,
                    username=username,
                    api_auth_token=api_auth_token,
                )
            # If one file was selected, no retrieval is needed
            else:
                selected_job_id = job_df[job_df.media_name == selected_media_name][
                    "UUID"
                ].values[0]
                full_transcript = retrieve_transcript_by_jobid(
                    job_id=selected_job_id,
                    username=username,
                    api_auth_token=api_auth_token,
                )
                full_answer = generate_answer_no_chunking(
                    query=user_message,
                    media_name=selected_media_name,
                    full_transcript=full_transcript,
                    api_auth_token=api_auth_token,
                )

    # If answer has any citations, automatically queue up the media to the first citation
    first_citation = None
    try:
        first_citation = full_answer.get_first_citation()
        media_url = retrieve_media_url(
            first_citation.media_name, username=username, api_auth_token=api_auth_token
        )
        display_video_at_timestamp(
            media_url,
            first_citation.timestamp,
        )
    except ValueError:
        pass

    # Draw any potential buttons beneath the video
    draw_or_redraw_citation_buttons(full_answer)

    # Display the assistant response
    assistant_message = full_answer.pprint()
    st.markdown(assistant_message)

    # Add assistant response to chat history
    st.session_state.messages.append(
        {"role": "assistant", "content": assistant_message}
    )
