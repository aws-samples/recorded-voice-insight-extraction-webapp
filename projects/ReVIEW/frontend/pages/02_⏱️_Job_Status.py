import streamlit as st
from components.db_utils import retrieve_all_items

st.set_page_config(
    page_title="Job Status",
    page_icon=":stopwatch:",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("Your Transcription Jobs")
st.write("Note: this page does not auto-refresh the transcription status.")
st.dataframe(
    retrieve_all_items(),
    hide_index=True,
    column_order=("media_name", "job_creation_time", "transcription_status"),
)
