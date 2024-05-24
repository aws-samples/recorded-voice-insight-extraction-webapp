import streamlit as st

logger = st.logger.get_logger(__name__)

st.set_page_config(
    page_title="ReVIEW",
    page_icon=":ear_with_hearing_aid:",
    layout="centered",
    initial_sidebar_state="expanded",
)

#########################
# SESSION STATE VARIABLES
#########################

st.session_state.setdefault("username", "")


def login():
    """Login with Cognito, set session state username variable"""
    st.session_state["username"] = "kazu"


def main():
    """
    Main app function
    """

    login()

    # input_col, output_col = st.columns([0.5, 0.5], gap="medium")
    st.title("Recorded Voice Insight Extraction Webapp")
    st.subheader("ReVIEW")
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
    st.subheader("Click on [ 💾 File Upload ] on the left to get started.")


def display_inputs(input_selection):
    """
    Display selected inputs
    """
    st.header("Inputs")
    st.json(input_selection)


if __name__ == "__main__":
    main()
