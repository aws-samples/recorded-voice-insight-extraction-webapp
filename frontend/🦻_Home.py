import streamlit as st
from components.cognito_utils import login

logger = st.logger.get_logger(__name__)

st.set_page_config(
    page_title="ReVIEW",
    page_icon=":ear_with_hearing_aid:",
    layout="centered",
    initial_sidebar_state="expanded",
)


def main():
    """
    Main app function
    """

    # input_col, output_col = st.columns([0.5, 0.5], gap="medium")
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


def display_inputs(input_selection):
    """
    Display selected inputs
    """
    st.header("Inputs")
    st.json(input_selection)


if __name__ == "__main__":
    main()
