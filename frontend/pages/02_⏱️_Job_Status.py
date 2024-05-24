import streamlit as st
from components.db_utils import retrieve_all_items
from components.cognito_utils import login
from components.streamlit_utils import display_sidebar

st.set_page_config(
    page_title="Job Status",
    page_icon=":stopwatch:",
    layout="centered",
    initial_sidebar_state="expanded",
)


st.title("Your Transcription Jobs")
if not st.session_state.get("auth_username", None):
    st.error("Please login to continue.")
    login()
    st.stop()
display_sidebar()

st.dataframe(
    retrieve_all_items(username=st.session_state["auth_username"]),
    hide_index=True,
    column_order=("media_name", "job_creation_time", "transcription_status"),
)

button_clicked = st.button("Refresh Table")
if button_clicked:
    # Refresh entire page on button click, just to reload the table
    st.rerun()
