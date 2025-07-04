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

"""Lambda to handle interactions with Bedrock foundation models"""

from bedrock.bedrock_utils import LLM
from lambda_utils.cors_utils import CORSResponse
from lambda_utils.invoke_lambda import invoke_lambda
import logging
import json
import boto3
import os

# Class to handle connections to Bedrock foundation models
llm = LLM()

logger = logging.getLogger()
logger.setLevel("INFO")

# Environment variables
DDB_LAMBDA_NAME = os.environ.get("DDB_LAMBDA_NAME")
S3_BUCKET = os.environ.get("S3_BUCKET")
TEXT_TRANSCRIPTS_PREFIX = os.environ.get("TEXT_TRANSCRIPTS_PREFIX")

# Create clients
lambda_client = boto3.client("lambda")
s3_client = boto3.client("s3")


def get_transcript_content(username: str, media_file_name: str) -> str:
    """Retrieve transcript content for a media file"""
    try:
        # First, get the job ID for this media file
        job_id = invoke_lambda(
            lambda_client=lambda_client,
            lambda_function_name=DDB_LAMBDA_NAME,
            action="retrieve_jobid_by_media_name",
            params={
                "media_name": media_file_name,
                "username": username,
            },
        )
        
        if not job_id:
            logger.warning(f"No job ID found for media file: {media_file_name}")
            return f"[Transcript not available for {media_file_name}]"
        
        # Get the transcript text file from S3
        transcript_key = f"{TEXT_TRANSCRIPTS_PREFIX}/{username}/{job_id}.txt"
        
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=transcript_key)
            transcript_content = response['Body'].read().decode('utf-8')
            return transcript_content
        except Exception as e:
            logger.warning(f"Could not retrieve transcript from S3: {transcript_key}, error: {str(e)}")
            return f"[Transcript not available for {media_file_name}]"
            
    except Exception as e:
        logger.error(f"Error retrieving transcript for {media_file_name}: {str(e)}")
        return f"[Error retrieving transcript for {media_file_name}]"



def lambda_handler(event, context):
    """
    Event will provide:
    * foundation model ID (str)
    * system_prompt (str)
    * main_prompt (str) - may contain {transcript} placeholder
    * bedrock keyword args (dict)
    * username (str) - for transcript retrieval
    * selectedFiles (list) - media files to analyze
    * template_id (str) - template identifier (not used for caching)

    Lambda returns a string generated by LLM
    """

    logger.debug(f"{event=}")

    try:
        if "body" in event:
            event = json.loads(event["body"])

        foundation_model_id = event["foundation_model_id"]
        system_prompt = event["system_prompt"]
        main_prompt = event["main_prompt"]
        bedrock_kwargs = event["bedrock_kwargs"]
        
        # Handle bedrock_kwargs - it might be a JSON string or already a dict
        if isinstance(bedrock_kwargs, str):
            try:
                bedrock_kwargs = json.loads(bedrock_kwargs)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse bedrock_kwargs JSON: {str(e)}")
                bedrock_kwargs = {}  # Use empty dict as fallback
        
        username = event.get("username", "")
        selected_files = event.get("selectedFiles", [])
        template_id = event.get("template_id")  # Keep for potential future use

        # If the prompt contains {transcript} placeholder, substitute it with actual transcript content
        if "{transcript}" in main_prompt and selected_files:
            # Get transcript content for all selected files
            transcript_contents = []
            for media_file in selected_files:
                transcript_content = get_transcript_content(username, media_file)
                transcript_contents.append(f"=== Transcript for {media_file} ===\n{transcript_content}")
            
            # Combine all transcripts
            combined_transcript = "\n\n".join(transcript_contents)
            
            # Replace the placeholder with actual transcript content
            main_prompt = main_prompt.replace("{transcript}", combined_transcript)
            logger.info(f"Substituted transcript content for {len(selected_files)} files")

        # Inference LLM & return result
        generation = llm.generate(
            model_id=foundation_model_id,
            system_prompt=system_prompt,
            prompt=main_prompt,
            kwargs=bedrock_kwargs,
        )
        
        return CORSResponse.success_response(generation)
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return CORSResponse.error_response(f"Internal server error: {str(e)}", 500)
