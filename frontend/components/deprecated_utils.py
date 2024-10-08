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

"""Deprecated utils saved here for posterity"""

import json
from bedrock_utils import get_bedrock_client, LLM
import os
import logging
import pandas as pd

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_analysis_templates() -> pd.DataFrame:
    """Read analysis templates (from csv for now, from db later) and return df"""
    dirname = os.path.dirname(__file__)  # Location of this python file
    analysis_templates_file_fullpath = os.path.join(
        dirname, "../assets/analysis_templates.csv"
    )
    return pd.read_csv(analysis_templates_file_fullpath)


def run_analysis(analysis_id: int, transcript: str, llm: LLM):
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
    return llm.generate(
        model_id=ana_model_id,
        system_prompt=system_prompt,
        prompt=ana_prompt,
        kwargs=ana_kwargs,
    )


def deprecated_chat_transcript_query(
    segmented_transcript: str, user_query: str, llm: LLM
) -> str:
    """Run a chat query on a segmented transcript string (see transcript_utils.py)
    and return the raw string. This function is generally deprecated as it does not use
    knowledge bases or chunking -- it copies the entire transcript of a single media
    file into the LLM context."""

    SYSTEM_PROMPT = """You are an intelligent AI which attempts to answer questions based on an automatically generated transcript."""

    CHAT_PROMPT_TEMPLATE = """<transcript>{transcript}</transcript>
    
    Each line in the transcript above includes an integer timestamp (in seconds) within square brackets, followed by a statement.
    
    Using only information in the above transcript, attempt to answer the question below.
    
    <question>{question}</question>
    
    Your response must contain two parts, an integer timestamp representing the start of the portion of the transcript which contains the answer to the question, and an answer to the question itself. The timestamp should be included within <timestamp></timestamp> tags, and the answer within <answer></answer> tags. If you are unable to answer the question, return a timestamp of -1 and an answer of "I am unable to find the answer to your question within the provided transcript."
    """

    chat_prompt = CHAT_PROMPT_TEMPLATE.format(
        transcript=segmented_transcript, question=user_query
    )

    # Inference LLM & return result
    return llm.generate(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        system_prompt=SYSTEM_PROMPT,
        prompt=chat_prompt,
        kwargs={"temperature": 0.1, "max_tokens": 200},
    )


def deprecated_retrieve_and_generate(query: str, username: str, media_name=None) -> str:
    """Unfortunately retrieve_and_generate API isn't flexible enough for this use case... its citations are nice, but
    require adding the $output_format_instructions$ variable, which overrides any other prompting (e.g. asking the LLM
    to return an answer and a timestamp). So. we'll use the retrieve API and do the generation ourselves to get the
    output format we want."""

    foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

    region_name = "us-east-1"

    bedrock_agent_runtime_client = get_bedrock_client(
        assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None),
        region=os.environ.get("AWS_DEFAULT_REGION", None),
        agent=True,
    )
    # return {"metadataAttributes": {"username": username, "media_name": media_name}}
    kb_id = os.environ["KNOWLEDGE_BASE_ID"]

    # Always filter on username to prevent people from querying other users' data
    # Optionally filter on media name if user wants to chat with just one media file
    username_filter = {"equals": {"key": "username", "value": username}}
    if not media_name:
        retrieval_filter = username_filter
    else:
        retrieval_filter = {
            "andAll": [
                username_filter,
                {"equals": {"key": "media_name", "value": media_name}},
            ]
        }

    retrieval_config = {
        "vectorSearchConfiguration": {"numberOfResults": 5, "filter": retrieval_filter},
    }

    CHAT_PROMPT_TEMPLATE = """You are an intelligent AI which attempts to answer questions based on retrieved chunks of automatically generated transcripts. 

    I will provide you with retrieved chunks of transcripts. The user will provide you with a question.
    
    Each line in the transcript chunk includes an integer timestamp (in seconds) within square brackets, followed by a transcribed sentence.
    
    Using only information in the provided transcript chunks, attempt to answer the user's question.

    Here are the retrieved chunks of transcripts in numbered order:
    <transcript_chunks>
    $search_results$
    </transcript_chunks>

    When you answer the question, your answer must contain only two parts: an integer timestamp representing the start of the portion of the transcript which contains the answer to the question, and an answer to the question itself. The timestamp should be included within <timestamp></timestamp> tags, and the answer within <answer></answer> tags.
    
    Here is the user's question:
    <question>$query$</question>

    $output_format_instructions$
    """

    response = bedrock_agent_runtime_client.retrieve_and_generate(
        input={"text": query},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": "arn:aws:bedrock:{}::foundation-model/{}".format(
                    region_name, foundation_model
                ),
                "retrievalConfiguration": retrieval_config,
                "generationConfiguration": {
                    "promptTemplate": {"textPromptTemplate": CHAT_PROMPT_TEMPLATE}
                },
            },
        },
    )
    """
    if you include $output_format_instructions$, the API will return the usual response["output"]["text"] which is just flat text, but it also returns response["citations"] which is a list of dicts containing some text, and the references that text came from. If you concatenate all of the texts from the citation list, you get back the full response["output"]["text"]
    Each citation element has "generatedResponsePart"."textResponsePart"."text", "retrievedReferences" list of dicts with "metadata"."media_name" (e.g. foo-bar.mp4)
    """
    return response["output"]["text"]
