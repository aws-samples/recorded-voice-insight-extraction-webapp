import streamlit as st
from components.db_utils import retrieve_all_items

st.set_page_config(
    page_title="Job Status",
    page_icon=":stopwatch:",
    layout="centered",
    initial_sidebar_state="expanded",
)
st.sidebar.title("Meeting Auto Summarizer")

st.subheader("Transcription Jobs")
st.dataframe(
    retrieve_all_items(),
    hide_index=True,
    column_order=("media_name", "job_creation_time", "transcription_status"),
)
