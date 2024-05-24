import streamlit as st
import streamlit_scrollable_textbox as stx
from components.bedrock_utils import LLM, get_analysis_templates, run_analysis
from components.db_utils import (
    retrieve_all_items,
    retrieve_analysis_by_jobid,
    store_analysis_result,
)
from components.s3_utils import retrieve_transcript_by_jobid

st.set_page_config(
    page_title="Media Analyzer",
    page_icon=":brain:",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("Analyze Your Media")
st.subheader("Pick a media file to analyze:")


@st.cache_resource
def get_LLM():
    return LLM()


if not st.session_state.get("username", None):
    st.error("You must be logged in to access this page.")
else:
    llm = get_LLM()

    job_df = retrieve_all_items(username=st.session_state["username"])
    completed_jobs = job_df[job_df.transcription_status == "Completed"]

    selected_media_name = st.selectbox(
        "dummy_label",
        options=completed_jobs.media_name,
        index=None,
        placeholder="Select a media file to analyze",
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
        selected_job_id = job_df[job_df.media_name == selected_media_name][
            "UUID"
        ].values[0]
        # Todo: make this better... fails e.g. if there are duplicate short analysis names
        selected_analysis_id = template_df[
            template_df.template_short_name == selected_analysis_name
        ].template_id.values[0]

        # If this analysis has already been run and the result is in dynamo, display it
        cached_results = retrieve_analysis_by_jobid(
            job_id=selected_job_id, template_id=selected_analysis_id
        )
        if cached_results:
            st.write("Displaying cached analysis result:")
            analysis_result = cached_results
        # Otherwise run the analysis and store the results in dynamo
        else:
            st.write("Analysis results will be displayed here when complete:")
            transcript = retrieve_transcript_by_jobid(job_id=selected_job_id)
            analysis_result = run_analysis(
                analysis_id=selected_analysis_id, transcript=transcript, llm=llm
            )
            store_analysis_result(
                job_id=selected_job_id,
                template_id=selected_analysis_id,
                analysis_result=analysis_result,
            )

        stx.scrollableTextbox(
            analysis_result,
            height=300,
        )
