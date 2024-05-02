import streamlit as st
import streamlit_scrollable_textbox as stx
from components.bedrock_utils import LLM, get_analysis_templates, run_analysis
from components.db_utils import retrieve_all_items
from components.s3_utils import retrieve_transcript_by_jobid

st.set_page_config(
    page_title="Meeting Analyzer",
    page_icon=":brain:",
    layout="centered",
    initial_sidebar_state="expanded",
)
st.sidebar.title("Meeting Auto Summarizer")
st.title("Analyze a Meeting")
st.subheader("Pick a meeting to analyze:")


@st.cache_resource
def get_LLM():
    return LLM()


llm = get_LLM()

job_df = retrieve_all_items()
completed_jobs = job_df[job_df.transcription_status == "Completed"]

selected_media_name = st.selectbox(
    "dummy_label",
    options=completed_jobs.media_name,
    index=None,
    placeholder="Select a meeting to analyze",
    label_visibility="collapsed",
)


st.subheader("Pick an analysis type:")
template_df = get_analysis_templates()
selected_analysis_name = st.selectbox(
    "dummy_label",
    options=template_df.template_short_name,
    index=None,
    placeholder="Select an analysis type",
    label_visibility="collapsed",
)


button_clicked = False
if selected_media_name and selected_analysis_name:
    button_clicked = st.button("Run Analysis")

if button_clicked:
    st.subheader("Analysis Results:")

    # Todo: make this better... fails e.g. if there are duplicate media names
    selected_job_id = job_df[job_df.media_name == selected_media_name]["UUID"].values[0]
    # Todo: make this better... fails e.g. if there are duplicate short analysis names
    selected_analysis_id = template_df[
        template_df.template_short_name == selected_analysis_name
    ].template_id.values[0]

    transcript = retrieve_transcript_by_jobid(job_id=selected_job_id)
    st.write("Analysis results will be displayed here when complete:")
    analysis_results = run_analysis(
        analysis_id=selected_analysis_id, transcript=transcript, llm=llm
    )
    stx.scrollableTextbox(
        analysis_results,
        height=300,
    )
