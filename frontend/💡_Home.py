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
from components.streamlit_utils import display_sidebar

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

    st.title("ReVIEW: Recorded Voice Insight Extraction Webapp")
    if not st.session_state.get("auth_username", None):
        st.info("Please login to continue.")
        login()
        st.stop()
    st.markdown(
        """
        This application allows you to upload audio or video recordings containing speech 
        and automatically generate different types of summaries or documents from
        transcripts of the recordings. 
        
        For example, you can generate a summary
        of an arbitrary recorded presentation, generate a discovery readout document from the recording of
        a discovery workshop, and more. 
        
        You can also "chat with your media"
        to ask arbitrary questions like _what did the speaker say about Sagemaker?_
        
        """
    )
    st.subheader("Click  💾 File Upload  on the left to get started.")
    display_sidebar()


def display_inputs(input_selection):
    """
    Display selected inputs
    """
    st.header("Inputs")
    st.json(input_selection)


if __name__ == "__main__":
    main()
