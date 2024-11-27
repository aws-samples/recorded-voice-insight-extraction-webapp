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

"""Helper utilities for working with Amazon Bedrock"""

import json
import os
import sys
import requests

# Add frontend dir to system path to import FullQAnswer
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
    )
)

from schemas.qa_response import FullQAnswer
from components.io_utils import get_analysis_templates

BACKEND_API_URL = os.environ["BACKEND_API_URL"]


def run_analysis(analysis_id: int, transcript: str, api_auth_token: str):
    """Run a predefined analysis (LLM generation) on a transcript"""

    # Get analysis template from csv
    template_df = get_analysis_templates()
    ana_series = template_df.set_index("template_id").loc[analysis_id]
    # Build prompt, set model ID, bedrock kwargs, etc
    system_prompt = ana_series["template_system_prompt"]
    ana_template = ana_series["template_string"]
    ana_prompt = ana_template.format(transcript=transcript)
    ana_kwargs = json.loads(ana_series["bedrock_kwargs"])
    ana_model_id = ana_series["model_id"]

    # Inference LLM & return result
    json_body = {
        "foundation_model_id": ana_model_id,
        "system_prompt": system_prompt,
        "main_prompt": ana_prompt,
        "bedrock_kwargs": ana_kwargs,
    }

    response = requests.post(
        BACKEND_API_URL + "/llm",
        json=json_body,
        headers={"Authorization": api_auth_token},
        timeout=30,
    )
    if response.status_code != 200:
        raise Exception(f"Non 200 response from API gateway: {response.text}")

    result = response.json()

    return result


def clean_messages(messages, max_number_of_messages=10):
    """Ensure messages list only has elements like {"role":"user", "cotent":[{"text":"blah}]},
    Also make sure <= max_number_of_messages latest messages are sent"""
    cleaned_messages = []
    for message in messages:
        cleaned_message = {
            "role": message.get("role"),
            "content": message.get("content"),
        }
        cleaned_messages.append(cleaned_message)
    return cleaned_messages[-max_number_of_messages:]


def retrieve_and_generate_answer(
    messages: list, username: str, api_auth_token: str
) -> FullQAnswer:
    """Query knowledge base and generate an answer. Only filter applied is
    the username (so each user can only query their own files)
    messages is list like [{"role": "user", "content": [{"text": "blah"}]}, {"role": "assistant", "content": ...}],
    """

    # Make sure only "role" and "content" fields are kept from the messages ... UI logic sometimes
    # adds other things in there to make the UI code more convenient
    json_body = {
        "messages": json.dumps(clean_messages(messages)),
        "username": username,
    }

    response = requests.post(
        BACKEND_API_URL + "/kb",
        json=json_body,
        headers={"Authorization": api_auth_token},
        timeout=30,
    )
    if response.status_code != 200:
        raise Exception(f"Non 200 response from API gateway: {response.text}")

    result = response.json()

    try:
        return FullQAnswer(**result)
    except Exception as e:
        print(f"Error parsing KB result: {str(e)}")
        raise


def generate_answer_no_chunking(
    messages: list, media_name: str, full_transcript: str, api_auth_token: str
) -> FullQAnswer:
    """Bypass the knowledge base, impute the full transcript into the prompt and have
    an LLM generate the answer. This function is used when user asks a question about
    one media file. Media name is provided only because it is included in
    the LLM-generated citations. KB lambda is used for convenience, as it has all of
    the prompt engineering / output parsing required to form FullQAnswer objects.
    messages is list like [{"role": "user", "content": [{"text": "blah"}]}, {"role": "assistant", "content": ...}],
    """

    json_body = {
        "messages": json.dumps(clean_messages(messages)),
        "full_transcript": full_transcript,
        "media_name": media_name,
    }
    response = requests.post(
        BACKEND_API_URL + "/kb",
        json=json_body,
        headers={"Authorization": api_auth_token},
        timeout=30,
    )
    if response.status_code != 200:
        raise Exception(f"Non 200 response from API gateway: {response.text}")

    result = response.json()

    try:
        return FullQAnswer(**result)
    except Exception as e:
        print(f"Error parsing LLM result: {str(e)}")
        raise
