import streamlit as st


logger = st.logger.get_logger(__name__)

st.set_page_config(
    page_title="Meeting Auto Summarizer",
    page_icon=":ear_with_hearing_aid:",
    layout="centered",
    initial_sidebar_state="expanded",
)


def main():
    """
    Main app function
    """

    # input_col, output_col = st.columns([0.5, 0.5], gap="medium")
    st.title("Meeting Auto Summarizer")
    st.subheader("Your personal meeting analysis tool")
    st.markdown(
        """
        This application allows you to upload audio or video recordings of meetings 
        and automatically generate different types of summaries or documents from
        the speech contained in the recordings. 
        
        For example, you can generate a summary
        of an arbitrary meeting, generate a discovery readout document from the recording of
        a discovery workshop, and more. 
        
        You can also "chat with your meeting"
        to ask arbitrary questions like _what follow-up action items were mentioned in the meeting?_
        
        Click on "File Upload" on the left to get started.
        """
    )
    with st.sidebar:
        display_sidebar()

    # with input_col:
    #     display_inputs(input_selection)


def display_sidebar():
    """
    Display sidebar where inputs can be selected
    """
    # This styling was copied from ADOSEA, not sure what it does
    # st.sidebar.markdown(
    #     """
    #     <style>
    #         [data-testid="stSidebarNav"]::before {
    #             content: "Tabs";
    #             margin-left: 20px;
    #             margin-top: 20px;
    #             margin-bottom: 20px;
    #             font-size: 22px;
    #             font-weight: bold;
    #             position: relative;
    #             top: 100px;
    #         }
    #     </style>
    #     """,
    #     unsafe_allow_html=True,
    # )

    # st.sidebar.success("Sidebar success")

    # input_index = st.sidebar.selectbox(
    #     "Select input",
    #     range(5),
    # )

    # # This returns true the moment the button is clicked, then will return false after that
    # button_pressed = st.button("Generate output", key="generate_output")

    # input_selection = {"input_index": input_index}
    # return input_selection, button_pressed

    st.sidebar.title("Meeting Auto Summarizer")
    return


def display_inputs(input_selection):
    """
    Display selected inputs
    """
    st.header("Inputs")
    st.json(input_selection)


if __name__ == "__main__":
    main()
