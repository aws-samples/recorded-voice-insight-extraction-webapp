import streamlit as st
from components.db_utils import retrieve_all_items

st.set_page_config(
    page_title="Meeting Analyzer",
    page_icon=":brain:",
    layout="centered",
    initial_sidebar_state="expanded",
)
st.sidebar.title("Meeting Auto Summarizer")
st.title("Analyze a Meeting")
st.subheader("Select a meeting to analyze")
st.subheader(" ** Not yet implemented ** ")

st.dataframe(
    retrieve_all_items(),
    hide_index=True,
    column_order=("media_name", "job_creation_time", "transcription_status"),
)
