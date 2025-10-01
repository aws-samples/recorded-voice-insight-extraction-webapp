# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import boto3
import botocore
from kb.kb_utils import KBQARAG

# Environment variables
KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
AWS_REGION = os.environ["AWS_REGION"]
NUM_CHUNKS = os.environ["NUM_CHUNKS"]
FOUNDATION_MODEL = os.environ["FOUNDATION_MODEL_ID"]
S3_BUCKET = os.environ.get("S3_BUCKET")
TEXT_TRANSCRIPTS_PREFIX = os.environ.get("TEXT_TRANSCRIPTS_PREFIX")
BDA_OUTPUT_PREFIX = os.environ.get("BDA_OUTPUT_PREFIX")

# Initialize clients
s3_client = boto3.client("s3")

# Initialize KB QA RAG handler
kbqarag = KBQARAG(
    knowledge_base_id=KNOWLEDGE_BASE_ID,
    region_name=AWS_REGION,
    num_chunks=NUM_CHUNKS,
    foundation_model=FOUNDATION_MODEL,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """Async Lambda to handle streaming LLM responses"""
    logger.info(f"Starting async streaming processor: {event}")
    
    try:
        # Extract parameters from event
        connection_id = event["connection_id"]
        endpoint_url = event["endpoint_url"]
        chat_input = event["chat_input"]
        user_id = event["user_id"]
        
        # Create API Gateway client for postToConnection
        gatewayapi = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint_url)
        
        def send_to_connection(data: dict):
            """Send data to WebSocket connection"""
            try:
                gatewayapi.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(data).encode("utf-8")
                )
                return True
            except Exception as e:
                logger.error(f"Failed to send to connection {connection_id}: {e}")
                return False

        # Process the chat input
        messages = json.loads(chat_input["messages"])
        username = chat_input.get("username", user_id)
        media_names = chat_input.get("media_names", [])
        if media_names:
            media_names = json.loads(media_names)
        transcript_job_id = chat_input.get("transcript_job_id", None)

        # Validate input
        if not (messages and username):
            raise ValueError("Missing required fields: messages and username")

        # If no specific media file is selected, use RAG over all files
        # If 2+ media files are selected, use RAG over just those files
        if len(media_names) == 0 or len(media_names) > 1:
            generation_stream = kbqarag.retrieve_and_generate_answer_stream(
                messages=messages,
                username=username,
                media_names=media_names,
            )
            for generation_event in generation_stream:
                if not send_to_connection(generation_event):
                    break

        else:  # Single media file selected
            # Retrieve the full transcript from S3
            logger.info(
                f"Retrieving transcript: s3://{S3_BUCKET}/{TEXT_TRANSCRIPTS_PREFIX}/{username}/{transcript_job_id}.txt"
            )
            full_transcript_from_s3 = (
                s3_client.get_object(
                    Bucket=S3_BUCKET,
                    Key=f"{TEXT_TRANSCRIPTS_PREFIX}/{username}/{transcript_job_id}.txt",
                )["Body"]
                .read()
                .decode("utf-8")
            )
            
            # Check for BDA output (for video files)
            try:
                bda_output = (
                    s3_client.get_object(
                        Bucket=S3_BUCKET,
                        Key=f"{BDA_OUTPUT_PREFIX}/{username}/{transcript_job_id}.txt",
                    )["Body"]
                    .read()
                    .decode("utf-8")
                )
            except botocore.exceptions.ClientError:
                logger.info(f"No BDA output exists for {transcript_job_id}")
                bda_output = ""

            generation_stream = kbqarag.generate_answer_no_chunking_stream(
                messages=messages,
                media_name=media_names[0],
                full_transcript=full_transcript_from_s3,
                bda_output=bda_output,
            )
            for generation_event in generation_stream:
                if not send_to_connection(generation_event):
                    break

        logger.info(f"Async streaming completed for connection {connection_id}")
        return {"statusCode": 200, "body": "Streaming completed"}

    except Exception as e:
        logger.exception(f"Failed in async streaming: {e}")
        
        # Try to send error to connection if possible
        try:
            connection_id = event.get("connection_id")
            endpoint_url = event.get("endpoint_url")
            if connection_id and endpoint_url:
                gatewayapi = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint_url)
                error_response = {
                    "status": "ERROR",
                    "reason": f"Failed to process request: {str(e)}",
                }
                gatewayapi.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(error_response).encode("utf-8")
                )
        except Exception as send_error:
            logger.error(f"Failed to send error to connection: {send_error}")
        
        return {"statusCode": 500, "body": f"Error: {str(e)}"}
