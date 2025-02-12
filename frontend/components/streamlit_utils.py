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

import os
from functools import lru_cache
import base64
import streamlit as st
from .cognito_utils import logout
from .s3_utils import retrieve_media_url, retrieve_transcript_by_jobid
from .bedrock_utils import (
    generate_answer_no_chunking,
    retrieve_and_generate_answer,
    generate_answer_no_chunking_stream,
    retrieve_and_generate_answer_stream,
)
import pandas as pd
from typing import Generator


def display_sidebar(current_page: str | None = None):
    sidebar = st.sidebar
    # If user is logged in, display a logout button
    if st.session_state.get("auth_username", None):
        check1 = sidebar.button("Logout")
        if check1:
            logout()
            st.rerun()

    # On the Chat With Your Media page, display a "clear conversation" button
    if current_page == "Chat With Your Media":
        if sidebar.button("Clear Conversation"):
            # Clear all messages
            st.session_state.messages = []
            # Reset citation state
            reset_citation_session_state()
            st.rerun()


def reset_citation_session_state():
    # Remove all citation button related stuff from session state variable
    # Create a list of keys to be removed
    keys_to_remove = [
        key for key in st.session_state.keys() if key.startswith("citation_")
    ]

    # Remove the keys from the dictionary
    for key in keys_to_remove:
        del st.session_state[key]

    st.session_state["n_buttons"] = 0


def any_buttons_visible() -> bool:
    # Check if any buttons are visible
    return any(k.startswith("citation_button_") for k in st.session_state.keys())


def draw_or_redraw_citation_buttons(full_answer, message_index: int):
    # Message_index is used to have a unique key for each button, with degrees of
    # freedom being message_index and citation_index
    # If a full_answer is provided, use it to draw buttons
    # if full_answer:
    all_citations = [
        citation
        for partial_answer in full_answer.answer
        for citation in partial_answer.citations
    ]

    n_buttons = len(all_citations)

    # Only draw buttons if there are any citations
    if n_buttons:
        cols = st.columns(n_buttons)
        buttons = []
        for i, (col, citation) in enumerate(zip(cols, all_citations), 1):
            with col:
                buttons.append(
                    st.button(f"{i}", key=f"citation_button_{message_index}-{i}")
                )
                st.session_state[f"citation_media_{message_index}-{i}"] = (
                    citation.media_name
                )
                st.session_state[f"citation_timestamp_{message_index}-{i}"] = (
                    citation.timestamp
                )


def display_video_at_timestamp(media_url, timestamp):
    if timestamp >= 0:
        # Note: this works for audio files, too.
        _video = st.video(
            data=media_url,
            start_time=timestamp,
        )


def display_full_ai_response(
    full_answer,
    username: str,
    api_auth_id_token: str,
    message_index: int,
    new_message: bool = True,
    media_name: str | None = None,
    start_timestamp: int | None = None,
):
    """Display video, citation buttons, and AI response text
    Also updates session state for new messages and citations"""

    # If a start_timestamp and media_name are provided, display that
    if start_timestamp and media_name:
        media_url = retrieve_media_url(
            media_name, username=username, api_auth_id_token=api_auth_id_token
        )
        display_video_at_timestamp(
            media_url,
            start_timestamp,
        )
    else:
        # If answer has any citations, automatically queue up the media to the first citation
        first_citation = None
        try:
            first_citation = full_answer.get_first_citation()
            media_url = retrieve_media_url(
                first_citation.media_name,
                username=username,
                api_auth_id_token=api_auth_id_token,
            )
            display_video_at_timestamp(
                media_url,
                first_citation.timestamp,
            )
        except AttributeError as e:
            print(f"AttributeError: {e}")
        except ValueError:
            pass

    # Draw any potential buttons beneath the video
    draw_or_redraw_citation_buttons(full_answer, message_index=message_index)

    # Display the assistant response
    assistant_message = full_answer.pprint()
    st.markdown(assistant_message)

    # Add assistant response to chat history for new message,
    # both the string and the full_answer object
    if new_message:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": [{"text": assistant_message}],
                "full_answer": full_answer,
            }
        )


def generate_full_answer(
    messages: list,
    username: str,
    api_auth_id_token: str,
    api_auth_access_token: str,
    selected_media_name: str | None = None,
    job_df: pd.DataFrame | None = None,
):
    """Given a user query, use GenAI to generate an answer.
    If selected_media_name and job_df are provided, download the full transcript and
    pass it to the LLM context (that is why job_df is required, it is used
    to find the UUID for the transcription job to get the transcript).
    If selected media_name is not provided, do RAG over all transcripts using the
    knowledge base.
    messages is list like [{"role": "user", "content": [{"text": "blah"}]}, {"role": "assistant", "content": ...}],
    """
    # If last message was from AI, insert empty AI message (this happens when exceptions are thrown in the UI)
    if messages[-1]["role"] == "assistant":
        messages.append({"role": "assistant", "content": [{"text": ""}]})

    # If no specific media file is selected, use RAG over all files
    if not selected_media_name:
        full_answer = retrieve_and_generate_answer(
            messages=messages,
            username=username,
            api_auth_access_token=api_auth_access_token,
        )
    # If one file was selected, no retrieval is needed
    else:
        selected_job_id = job_df[job_df.media_name == selected_media_name][
            "UUID"
        ].values[0]
        full_transcript = retrieve_transcript_by_jobid(
            job_id=selected_job_id,
            username=username,
            api_auth_token=api_auth_id_token,
        )
        full_answer = generate_answer_no_chunking(
            messages=messages,
            media_name=selected_media_name,
            full_transcript=full_transcript,
            api_auth_token=api_auth_access_token,
        )
    return full_answer


def generate_full_answer_stream(
    messages: list,
    username: str,
    api_auth_id_token: str,  # Auth token used for REST API to retrieve transcript
    api_auth_access_token: str,  # Auth used for WS connection
    selected_media_name: str | None = None,
    job_df: pd.DataFrame | None = None,
) -> Generator[str, None, None]:
    """Given a user query, use GenAI to generate an answer."""
    # If last message was from AI, insert empty AI message
    if messages[-1]["role"] == "assistant":
        messages.append({"role": "assistant", "content": [{"text": ""}]})

    # If no specific media file is selected, use RAG over all files
    if not selected_media_name:
        yield from retrieve_and_generate_answer_stream(
            messages=messages,
            username=username,
            api_auth_access_token=api_auth_access_token,
        )
    # If one file was selected, no retrieval is needed
    else:
        selected_job_id = job_df[job_df.media_name == selected_media_name][
            "UUID"
        ].values[0]
        full_transcript = retrieve_transcript_by_jobid(
            job_id=selected_job_id,
            username=username,
            api_auth_id_token=api_auth_id_token,
        )
        yield from generate_answer_no_chunking_stream(
            messages=messages,
            media_name=selected_media_name,
            full_transcript=full_transcript,
            api_auth_access_token=api_auth_access_token,
        )


@lru_cache
def get_banner_image_content():
    """Load banner image into base64 string to display easily within html"""
    # Construct the relative path to the image from this script
    this_script_dir = os.path.dirname(os.path.realpath(__file__))
    full_image_path = os.path.join(
        this_script_dir, "..", "assets", "ReVIEW-UI-banner.png"
    )
    image_file = open(full_image_path, "rb")
    # file_ = open("/home/rzwitch/Desktop/giphy.gif", "rb")
    image_contents = image_file.read()
    image_data_url = base64.b64encode(image_contents).decode("utf-8")
    image_file.close()
    return image_data_url


def show_cover(
    title: str,
    description: str = "",
    max_width: str = "100%",
    text_color: str = "#FFFFFF",
) -> None:
    """
    Display cover image with title & description

    Parameters
    ----------
    title : str
        Title to display over the image (upper part)
    description : str
        Description to display over the image (lower part)
    max_width : str
        Maximum width of the cover image
    text_color : str
        Code of the title & description font color
    """

    banner_image_content = get_banner_image_content()
    html_code = f"""
    <div class="container" align="center">
    <img src="data:image/gif;base64,{banner_image_content}" alt="Cover" style="max-width:{max_width};">
    <div style="position: absolute; top: 8px; left: 32px; font-size: 3rem; font-weight: bold; color: {text_color}" align="center">{title}</div>
    <div style="position: absolute; bottom: 8px; left: 32px; font-size: 1.5rem; color: {text_color}" align="center">{description}</div>
    </div>
    """
    st.markdown(
        html_code,
        unsafe_allow_html=True,
    )
