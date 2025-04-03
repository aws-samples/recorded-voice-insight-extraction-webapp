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
from .s3_utils import retrieve_media_url, retrieve_subtitles_by_jobid
from .db_utils import retrieve_jobid_by_media_name
import urllib.parse

LANGUAGE_OPTIONS = (
    "Bulgarian",
    "Croatian",
    "Czech",
    "Danish",
    "Dutch",
    "English",
    "Estonian",
    "Finnish",
    "French",
    "German",
    "Greek",
    "Hungarian",
    "Irish",
    "Italian",
    "Latvian",
    "Lithuanian",
    "Maltese",
    "Polish",
    "Portuguese",
    "Romanian",
    "Slovak",
    "Slovenian",
    "Spanish",
    "Swedish",
)


def initialize_session_state():
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_media_names" not in st.session_state:
        st.session_state.selected_media_names = None
    if "display_subtitles" not in st.session_state:
        st.session_state.display_subtitles = False
    if "translation_destination_language" not in st.session_state:
        st.session_state.translation_destination_language = None


def reset_and_rerun_page():
    # Clear all messages
    st.session_state.messages = []
    # Reset citation state
    reset_citation_session_state()
    st.rerun()


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
            reset_and_rerun_page()
        st.session_state.display_subtitles = sidebar.checkbox(
            "Display subtitles in videos"
        )
        if st.session_state.display_subtitles:
            st.session_state.translation_destination_language = sidebar.selectbox(
                "Translate subtitles?",
                LANGUAGE_OPTIONS,
                index=None,
                placeholder="Select a language",
            )


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


def display_video_at_timestamp(
    media_url,
    timestamp,
    api_auth_id_token: str | None = None,
    username: str | None = None,
):
    """Display video starting at timestamp.
    Username, api_auth_access_token are only needed if display_subtitles is true, because
    this function hits an API endpoint to get the subtitles from the backend
    """
    # If display_subtitles, retrieve job_id based on media_url, then retrieve vtt subtitles
    subtitles_string = None
    display_subtitles = st.session_state.display_subtitles
    if display_subtitles:
        # Note media_url is a presigned url
        media_name = urllib.parse.unquote(
            urllib.parse.urlparse(media_url).path.split("/")[-1]
        )

        job_id = retrieve_jobid_by_media_name(
            username=username,
            media_name=media_name,
            api_auth_id_token=api_auth_id_token,
        )

        translation_start_time = None
        translation_duration = None
        translation_destination_language = None
        if st.session_state.translation_destination_language:
            translation_start_time = timestamp
            translation_duration = 60  # seconds
            translation_destination_language = (
                st.session_state.translation_destination_language
            )
        # Retrieve subtitles, optionally translating them
        # (let the user know if translation is happening
        #  because this adds significant latency to the
        #  video playback experience)
        if translation_destination_language:
            st.toast("Translating subtitles...")

        subtitles_string = retrieve_subtitles_by_jobid(
            job_id=job_id,
            username=username,
            api_auth_id_token=api_auth_id_token,
            translation_start_time=translation_start_time,
            translation_duration=translation_duration,
            translation_destination_language=translation_destination_language,
        )

    if timestamp >= 0:
        # Note: this works for audio files, too.
        video_kwargs = {"data": media_url, "start_time": timestamp}
        if subtitles_string:
            video_kwargs["subtitles"] = subtitles_string
        _video = st.video(**video_kwargs)


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
            username=username,
            api_auth_id_token=api_auth_id_token,
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
                username=username,
                api_auth_id_token=api_auth_id_token,
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
