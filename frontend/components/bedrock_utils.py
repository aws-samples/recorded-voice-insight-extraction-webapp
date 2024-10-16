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

import boto3
import pandas as pd

# Add frontend dir to system path to import FullQAnswer
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
    )
)

from schemas.qa_response import FullQAnswer

# Create a Lambda client
lambda_client = boto3.client("lambda")


# TODO: replace with API gateway
def invoke_llm_lambda(params):
    lambda_params = {
        "FunctionName": "review-dev-339712833620-LLMHandlerLambda",  # API gateway knows this
        "InvocationType": "RequestResponse",
        "Payload": json.dumps({**params}),
    }
    try:
        response = lambda_client.invoke(**lambda_params)
        return json.loads(response["Payload"].read().decode("utf-8"))
    except Exception as e:
        print(f"Error invoking Lambda: {str(e)}")
        raise


# TODO: replace with API gateway
def invoke_kb_lambda(params):
    lambda_params = {
        "FunctionName": "review-dev-339712833620-KBQueryLambda",  # API gateway knows this
        "InvocationType": "RequestResponse",
        "Payload": json.dumps({**params}),
    }
    try:
        response = lambda_client.invoke(**lambda_params)
        return json.loads(response["Payload"].read().decode("utf-8"))
    except Exception as e:
        print(f"Error invoking Lambda: {str(e)}")
        raise


def get_analysis_templates() -> pd.DataFrame:
    """Read analysis templates (from csv for now, from db later) and return df"""
    dirname = os.path.dirname(__file__)  # Location of this python file
    analysis_templates_file_fullpath = os.path.join(
        dirname, "../assets/analysis_templates.csv"
    )
    return pd.read_csv(analysis_templates_file_fullpath)


def run_analysis(analysis_id: int, transcript: str):
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
    return invoke_llm_lambda(
        {
            "foundation_model_id": ana_model_id,
            "system_prompt": system_prompt,
            "main_prompt": ana_prompt,
            "bedrock_kwargs": ana_kwargs,
        }
    )


def retrieve_and_generate_answer(query: str, username: str) -> FullQAnswer:
    """Query knowledge base and generate an answer. Only filter applied is
    the username (so each user can only query their own files)"""

    lambda_response = invoke_kb_lambda(
        {
            "query": query,
            "username": username,
        }
    )
    return FullQAnswer(**lambda_response)


def generate_answer_no_chunking(
    query: str, media_name: str, full_transcript: str
) -> FullQAnswer:
    """Bypass the knowledge base, impute the full transcript into the prompt and have
    an LLM generate the answer. This function is used when user asks a question about
    one media file. Media name is provided only because it is included in
    the LLM-generated citations. KB lambda is used for convenience, as it has all of
    the prompt engineering / output parsing required to form FullQAnswer objects."""

    lambda_response = invoke_kb_lambda(
        {
            "query": query,
            "full_transcript": full_transcript,
            "media_name": media_name,
        }
    )

    return FullQAnswer(**lambda_response)
