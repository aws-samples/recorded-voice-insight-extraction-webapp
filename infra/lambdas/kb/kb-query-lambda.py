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

"""Lambda to handle interactions with Bedrock Knowledge Base"""

import os
from kb.kb_utils import KBQARAG
import logging
import json

KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
AWS_REGION = os.environ["AWS_REGION"]
NUM_CHUNKS = os.environ["NUM_CHUNKS"]
FOUNDATION_MODEL = os.environ["FOUNDATION_MODEL_ID"]


# Class to handle connections to Bedrock and QA RAG workflow processes
kbqarag = KBQARAG(
    knowledge_base_id=KNOWLEDGE_BASE_ID,
    region_name=AWS_REGION,
    num_chunks=NUM_CHUNKS,
    foundation_model=FOUNDATION_MODEL,
)

logger = logging.getLogger()
logger.setLevel("DEBUG")


def lambda_handler(event, context):
    """
    Event will provide either:
    * query and username (to query all media uploaded by that user)

    OR
    * query, media_name, and full_transcript (to query one specific file)

    Lambda returns a json which can be parsed into a FullQAnswer object like
    answer = FullQAnswer(**lambda_response)
    """
    query = event["query"]
    username = event.get("username", None)
    media_name = event.get("media_name", None)
    full_transcript = event.get("full_transcript", None)

    assert (query and username) or (query and media_name and full_transcript)

    # If no specific media file is selected, use RAG over all files
    if not media_name:
        full_answer: dict = kbqarag.retrieve_and_generate_answer(
            query=query,
            username=username,
            media_name=None,
        )
    # If one file was selected, no knowledge base or retrieval is needed,
    # pass the full transcript in to an LLM for generation
    # Media name is provided for use in the LLM-generated citations
    else:
        full_answer: dict = kbqarag.generate_answer_no_chunking(
            query=query,
            media_name=media_name,
            full_transcript=full_transcript,
        )
    return {"statusCode": 200, "body": json.dumps(full_answer)}
