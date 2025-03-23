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

import boto3
import os
from kb.kb_utils import KBQARAG
import logging
import json

KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
AWS_REGION = os.environ["AWS_REGION"]
NUM_CHUNKS = os.environ["NUM_CHUNKS"]
FOUNDATION_MODEL = os.environ["FOUNDATION_MODEL_ID"]
WEBSOCKET_API_URL = os.environ["WS_API_URL"]
S3_BUCKET = os.environ.get("S3_BUCKET")
TEXT_TRANSCRIPTS_PREFIX = os.environ.get("TEXT_TRANSCRIPTS_PREFIX")

# Class to handle connections to Bedrock and QA RAG workflow processes
kbqarag = KBQARAG(
    knowledge_base_id=KNOWLEDGE_BASE_ID,
    region_name=AWS_REGION,
    num_chunks=NUM_CHUNKS,
    foundation_model=FOUNDATION_MODEL,
)
api_client = boto3.client(
    "apigatewaymanagementapi",
    endpoint_url=WEBSOCKET_API_URL,
    region_name=AWS_REGION,
)

# This lambda needs access to s3 because in some cases it GETs transcripts from there
s3_client = boto3.client("s3")

logger = logging.getLogger()
logger.setLevel("INFO")


def stream_lambda_handler(event, context):
    """
    Event will provide either:
    * query and username (to query all media uploaded by that user)

    OR
    * query, media_names, and transcript_job_id (to query one or more specific files)

    Lambda returns a json which can be parsed into a FullQAnswer object like
    answer = FullQAnswer(**lambda_response)
    """
    # When this lambda is called by the frontend via API gateway, the event
    # has a 'body' key. When this lambda is called by other lambdas, this is
    # unnecessary

    logger.debug(f"{event=}")
    connection_id = event["requestContext"]["connectionId"]

    if "body" in event:
        event = json.loads(event["body"])

    messages = json.loads(event["messages"])
    username = event.get("username", None)
    media_names = event.get("media_names", None)
    if media_names:
        media_names = json.loads(media_names)
    transcript_job_id = event.get("transcript_job_id", None)

    assert (messages and username) or (
        messages and media_names and transcript_job_id and username
    )

    # If no specific media file is selected, use RAG over all files
    # If 2+ media files are selected, use RAG over just those files
    if not media_names or len(media_names) > 1:
        try:
            generation_stream = kbqarag.retrieve_and_generate_answer_stream(
                messages=messages,
                username=username,
                media_names=media_names,  # media_names can be None or a list of length > 1 here
            )
            for generation_event in generation_stream:
                # Serialize the dictionary to a JSON string and encode to bytes
                data = json.dumps(generation_event).encode("utf-8")
                api_client.post_to_connection(Data=data, ConnectionId=connection_id)
        except Exception as e:
            return {"statusCode": 500, "body": f"Internal server error: {e}"}

    else:  # media_name is a list of length 1 here
        try:
            # Retrieve the full_transcript from the job_id
            # Get the object from S3
            logger.info(
                f"Attempting to retrieve: s3://{S3_BUCKET}/{TEXT_TRANSCRIPTS_PREFIX}/{username}/{transcript_job_id}.txt"
            )
            full_transcript_from_s3 = (
                s3_client.get_object(
                    Bucket=S3_BUCKET,
                    Key=f"{TEXT_TRANSCRIPTS_PREFIX}/{username}/{transcript_job_id}.txt",
                )["Body"]
                .read()
                .decode("utf-8")
            )
            generation_stream = kbqarag.generate_answer_no_chunking_stream(
                messages=messages,
                media_name=media_names[0],  # media_name is a string here
                full_transcript=full_transcript_from_s3,
            )
            for generation_event in generation_stream:
                # Serialize the dictionary to a JSON string and encode to bytes
                data = json.dumps(generation_event).encode("utf-8")
                api_client.post_to_connection(Data=data, ConnectionId=connection_id)
        except Exception as e:
            return {"statusCode": 500, "body": f"Internal server error: {e}"}

    logger.info(f"Closing connection {connection_id}")
    api_client.delete_connection(ConnectionId=connection_id)
    return {"statusCode": 200, "body": "Success"}
