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
import streamlit_scrollable_textbox as stx
from components.bedrock_utils import run_analysis
from components.cognito_utils import login
from components.db_utils import (
    retrieve_all_items,
    retrieve_analysis_by_jobid,
    store_analysis_result,
)
from components.io_utils import get_analysis_templates
from components.s3_utils import retrieve_transcript_by_jobid
from components.streamlit_utils import display_sidebar, show_cover

st.set_page_config(
    page_title="Media Analyzer",
    page_icon=":brain:",
    layout="centered",
    initial_sidebar_state="expanded",
)
show_cover(title="ReVIEW", description="Analyze Your Media")

if not st.session_state.get("auth_username", None):
    st.error("Please login to continue.")
    login()
    st.stop()
st.subheader("Pick a media file to analyze:")
display_sidebar()

username = st.session_state["auth_username"]
api_auth_id_token = st.session_state["auth_id_token"]

job_df = retrieve_all_items(
    username=username,
    max_rows=None,
    api_auth_id_token=api_auth_id_token,
)
completed_jobs = job_df[job_df.job_status == "Completed"]

selected_media_name = st.selectbox(
    "kazu",
    options=completed_jobs.media_name,
    index=None,
    placeholder="Select a media file to analyze",
    label_visibility="collapsed",
)

st.subheader("Pick an analysis type:")
template_df = get_analysis_templates()
selected_analysis_name = st.selectbox(
    "kazu",
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

    # TODO: this fails e.g. if there are duplicate media names
    selected_job_id = job_df[job_df.media_name == selected_media_name]["UUID"].values[0]
    # TODO: this fails e.g. if there are duplicate short analysis names
    selected_analysis_id = template_df[
        template_df.template_short_name == selected_analysis_name
    ].template_id.values[0]

    # If this analysis has already been run and the result is in dynamo, display it
    cached_results = retrieve_analysis_by_jobid(
        job_id=selected_job_id,
        username=username,
        template_id=selected_analysis_id,
        api_auth_id_token=api_auth_id_token,
    )
    if cached_results:
        st.info("Displaying cached analysis result:")
        analysis_result = cached_results
    # Otherwise run the analysis and store the results in dynamo
    else:
        st.info("Analysis results will be displayed here when complete:")

        transcript = retrieve_transcript_by_jobid(
            job_id=selected_job_id,
            username=username,
            api_auth_id_token=api_auth_id_token,
        )
        analysis_result = run_analysis(
            analysis_id=selected_analysis_id,
            transcript=transcript,
            api_auth_id_token=api_auth_id_token,
        )
        store_analysis_result(
            job_id=selected_job_id,
            username=username,
            template_id=selected_analysis_id,
            analysis_result=analysis_result,
            api_auth_id_token=api_auth_id_token,
        )

    stx.scrollableTextbox(
        analysis_result,
        height=300,
    )
