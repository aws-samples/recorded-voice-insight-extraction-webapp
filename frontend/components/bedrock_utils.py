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

import re
import json
import os
import sys
import requests  # for REST API
import websocket  # for streaming WS API
from typing import Generator

# Add frontend dir to system path to import FullQAnswer
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
    )
)

from schemas.qa_response import FullQAnswer
from components.io_utils import get_analysis_templates


BACKEND_API_URL = os.environ["BACKEND_API_URL"]
WS_API_URL = os.environ["WS_API_URL"]


class WebsocketTimeoutError(Exception):
    """Exception raised when the websocket connection times out."""

    pass


def run_analysis(analysis_id: int, transcript: str, api_auth_id_token: str):
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
        headers={"Authorization": api_auth_id_token},
        timeout=30,
    )
    if response.status_code != 200:
        raise Exception(f"Non 200 response from API gateway: {response.text}")

    result = response.json()

    return result


def clean_messages(messages, max_number_of_messages=10):
    """Ensure messages list only has elements like {"role":"user", "content":[{"text":"blah}]},
    Also make sure <= max_number_of_messages latest messages are sent.
    Also make sure the first element in messages is a user message.
    Also remove any citations in the content, for example if a message has content
    "This is the first sentence[1][2]." that will be cleaned to "This is the first sentence."
    """
    cleaned_messages = []
    for message in messages:
        content_str = message.get("content")[0]["text"]
        cleaned_content_str = re.sub(r"\[\d+\]", "", content_str)
        cleaned_message = {
            "role": message.get("role"),
            "content": [{"text": cleaned_content_str}],
        }
        cleaned_messages.append(cleaned_message)

    cleaned_messages = cleaned_messages[-max_number_of_messages:]

    while cleaned_messages[0]["role"] != "user":
        _ = cleaned_messages.pop(0)

    return cleaned_messages


def retrieve_and_generate_answer_stream(
    messages: list,
    media_names: list[str] | None,
    username: str,
    api_auth_access_token: str,
) -> Generator[FullQAnswer, None, None]:
    """Query knowledge base and generate an answer (streaming WS API). Only filter applied is
    the username (so each user can only query their own files)
    messages is list like [{"role": "user", "content": [{"text": "blah"}]}, {"role": "assistant", "content": ...}],
    """
    json_body = {
        "action": "$default",
        "messages": json.dumps(clean_messages(messages)),
        "username": username,
    }
    if media_names is not None:
        json_body["media_names"] = json.dumps(media_names)

    yield from websocket_stream(json_body, api_auth_access_token=api_auth_access_token)


def generate_answer_no_chunking_stream(
    messages: list,
    media_name: str,
    username: str,
    transcript_job_id: str,
    api_auth_access_token: str,
) -> Generator[FullQAnswer, None, None]:
    """Bypass the knowledge base, impute the full transcript into the prompt and have
    an LLM generate the answer. This function is used when user asks a question about
    one media file. Media name is provided only because it is included in
    the LLM-generated citations. KB lambda is used for convenience, as it has all of
    the prompt engineering / output parsing required to form FullQAnswer objects.
    Full transcript is not provided as input to this function due to maximum
    allowable websocket payload size:
    https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-known-issues.html#api-gateway-known-issues-websocket-apis
    messages is list like [{"role": "user", "content": [{"text": "blah"}]}, {"role": "assistant", "content": ...}],
    """
    json_body = {
        "action": "$default",
        "messages": json.dumps(clean_messages(messages)),
        "transcript_job_id": transcript_job_id,
        "username": username,
        "media_names": json.dumps([media_name]),
    }
    yield from websocket_stream(json_body, api_auth_access_token=api_auth_access_token)


def websocket_stream(
    json_body: dict, api_auth_access_token: str
) -> Generator[FullQAnswer, None, None]:
    """Stream from websocket, parse response into FullQAnswer objects"""
    ws = None

    try:
        # Create headers with the bearer token
        headers = {"Authorization": f"Bearer {api_auth_access_token}"}

        try:
            ws = websocket.create_connection(
                url=WS_API_URL,
                header=headers,
                enable_multithread=True,
            )
        except websocket.WebSocketBadStatusException:
            raise

        ws.send(json.dumps(json_body))

        while True:
            response = ws.recv()

            try:
                # First parse the response to check for timeout error
                parsed_response = json.loads(response)

                # Check if this is the specific timeout error
                if (
                    isinstance(parsed_response, dict)
                    and parsed_response.get("message") == "Endpoint request timed out"
                ):
                    raise WebsocketTimeoutError("Endpoint request timed out")

                # Otherwise, process as normal
                yield FullQAnswer(**parsed_response)

            except WebsocketTimeoutError:
                # Re-raise the timeout error to be caught by the frontend
                raise
            except Exception as e:
                if response:
                    print(f"Error parsing this into FullQAnswer: {response=}")
                    raise Exception(f"Error: {response}") from e
                else:
                    continue

    except websocket.WebSocketConnectionClosedException:
        # print("Connection closed")
        pass
    except WebsocketTimeoutError:
        # Re-raise to be caught by the frontend
        raise
    except websocket.WebSocketBadStatusException:
        raise Exception(
            "Your authentication has expired. Please refresh the page and log in again."
        )

    except Exception as e:
        # The last response from ws is always an empty string, which doesn't parse as FullQAnswer,
        # so this block is to ignore that
        if str(e) != "Expecting value: line 1 column 1 (char 0)":
            raise e
    finally:
        if ws:
            ws.close()
