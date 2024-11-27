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

logger = st.logger.get_logger(__name__)

st.set_page_config(
    page_title="ReVIEW",
    page_icon=":bulb:",
    layout="centered",
    initial_sidebar_state="expanded",
)


def main():
    """
    Main app function
    """

    show_cover(title="ReVIEW", description="Recorded Voice Insight Extraction Webapp")

    if not st.session_state.get("auth_username", None):
        st.info("Please login to continue.")
        login()
        st.stop()
    st.write("\n\n")

    html_string = """
    <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 200px;">
        <p style="font-style: italic; font-size: 22px; text-align: center;">
            Upload audio or video recordings containing speech and review them in an accelerated manner, either by running customized analyses on them, or by chatting with them directly.
        </p>
        <p style="font-weight: bold; font-size: 26px; text-align: center; margin-top: 20px;">
            Click  💾 File Upload  on the left to get started.
        </p>
    </div>
    """
    st.markdown(html_string, unsafe_allow_html=True)
    display_sidebar()


def display_inputs(input_selection):
    """
    Display selected inputs
    """
    st.header("Inputs")
    st.json(input_selection)


if __name__ == "__main__":
    main()
