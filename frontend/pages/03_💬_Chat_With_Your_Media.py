import streamlit as st
from components.bedrock_utils import LLM, chat_transcript_query
from components.db_utils import (
    retrieve_all_items,
)
from components.parsing_utils import extract_timestamp_and_answer
from components.s3_utils import retrieve_media_bytes, retrieve_transcript_json_by_jobid
from components.transcripts_utils import build_timestamped_segmented_transcript

st.set_page_config(
    page_title="Chat With Your Media",
    page_icon=":speech_balloon:",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("Chat with Your Media")
st.subheader("Pick a media file to chat with:")


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
        placeholder="Select a media file to chat with",
        label_visibility="collapsed",
    )

    if selected_media_name:
        media_bytes = retrieve_media_bytes(
            selected_media_name, username=st.session_state["username"]
        )

        if user_message := st.chat_input(placeholder="Enter your question here"):
            with st.chat_message("user"):
                st.write(user_message)
            selected_job_id = job_df[job_df.media_name == selected_media_name][
                "UUID"
            ].values[0]
            transcript_json = retrieve_transcript_json_by_jobid(job_id=selected_job_id)
            segmented_transcript_str = build_timestamped_segmented_transcript(
                transcript_json
            )

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    llm_response = chat_transcript_query(
                        segmented_transcript=segmented_transcript_str,
                        user_query=user_message,
                        llm=llm,
                    )

                    answer, timestamp_int = extract_timestamp_and_answer(llm_response)
                if timestamp_int >= 0:
                    video = st.video(
                        data=media_bytes,
                        start_time=timestamp_int,
                    )
                st.write(answer)
