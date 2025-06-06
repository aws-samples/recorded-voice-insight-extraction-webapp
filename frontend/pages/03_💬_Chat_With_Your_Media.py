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
from components.db_utils import retrieve_all_items
import components.streamlit_utils as stu
import components.bedrock_utils as bru
from components.bedrock_utils import WebsocketTimeoutError

st.set_page_config(
    page_title="Chat With Your Media",
    page_icon=":speech_balloon:",
    layout="centered",
    initial_sidebar_state="expanded",
)

stu.show_cover(title="ReVIEW", description="Chat with Your Media")

if not st.session_state.get("auth_username", None):
    st.error("Please login to continue.")
    login()
    st.stop()

stu.initialize_session_state()

username = st.session_state["auth_username"]
api_auth_id_token = st.session_state["auth_id_token"]
api_auth_access_token = st.session_state["auth_access_token"]

st.subheader("Pick media file to analyze:")
stu.display_sidebar(current_page="Chat With Your Media")

job_df = retrieve_all_items(
    username=username, max_rows=None, api_auth_id_token=api_auth_id_token
)
completed_jobs = job_df[
    (job_df.job_status == "Completed") | (job_df.job_status == "BDA Analysis Complete")
]

CHAT_WITH_ALL_STRING = "Chat with all media files"
selected_media_names = st.multiselect(  # This is an empty list if nothing is selected
    "kazu",
    options=sorted(completed_jobs.media_name.to_list()),  # Display alphabetically
    placeholder=CHAT_WITH_ALL_STRING,
    label_visibility="collapsed",
)

# If the user is in the middle of a conversation and they change selected_media_names,
# reset the conversation
if (
    st.session_state.messages
    and selected_media_names != st.session_state.selected_media_names
):
    stu.reset_and_rerun_page()


st.session_state.selected_media_names = selected_media_names

# Display chat messages from history on app rerun
# Use special function to display AI messages
# Whilst redrawing, check if any buttons were pressed and act accordingly
for message_counter, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"][0]["text"])
        else:  # AI messages
            media_name = None
            start_timestamp = None
            # Check if any buttons are pressed
            for k, v in st.session_state.items():
                # If this button is pressed, show video
                if k.startswith("citation_button_") and v:
                    clicked_citation_index = k.split("_")[
                        -1
                    ]  # e.g. 1-2 for button #2 for message #1
                    clicked_citation_media = st.session_state[
                        f"citation_media_{clicked_citation_index}"
                    ]
                    clicked_citation_timestamp = st.session_state[
                        f"citation_timestamp_{clicked_citation_index}"
                    ]
                    # Display the appropriate video at the appropriate timestamp
                    media_name = clicked_citation_media
                    start_timestamp = clicked_citation_timestamp
                    break
            # Display AI response, if buttons were not pressed then
            # media_name and start_timestamp are None, so the first citation
            # from the full_answer is used by default
            stu.display_full_ai_response(
                full_answer=message["full_answer"],
                username=username,
                api_auth_id_token=api_auth_id_token,
                message_index=message_counter,
                new_message=False,
                media_name=media_name,
                start_timestamp=start_timestamp,
            )

# If the user has just typed a new message
if user_message := st.chat_input(placeholder="Enter your question here"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.write(user_message)
    # Add user message to chat history
    st.session_state.messages.append(
        {"role": "user", "content": [{"text": user_message}]}
    )
    # Display streaming assistant response in chat message container
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                full_answer_iterator = bru.retrieve_and_generate_answer_stream(
                    messages=st.session_state.messages,
                    media_names=selected_media_names,
                    username=username,
                    api_auth_access_token=api_auth_access_token,  # Access token used for WS API authorization
                    job_df=job_df,
                )
                placeholder = st.empty()
                # current_full_answer grows in size as stream continues, so repeatedly
                # display the full answer (excluding citations) as the stream progresses
                current_full_answer = next(full_answer_iterator, None)
                while current_full_answer is not None:
                    next_full_answer = next(full_answer_iterator, None)

                    if next_full_answer is not None:
                        placeholder.markdown(current_full_answer.pprint())
                    else:
                        break

                    current_full_answer = next_full_answer
            except WebsocketTimeoutError:
                st.warning(
                    "Warning: Response truncated due to API Gateway Websocket Timeout. Showing partial results."
                )

            # Display the final full, complete answer with citations and media players
            # (or, last valid answer we received, if WebsocketTimeoutError)
            # Also adds the AI message to st.session_state.messages
            if current_full_answer:  # Ensure we have a valid answer to display
                stu.display_full_ai_response(
                    full_answer=current_full_answer,
                    username=username,
                    api_auth_id_token=api_auth_id_token,
                    message_index=len(st.session_state.messages),
                )

            # Empty the old placeholder to avoid duplicating the message
            placeholder.empty()
