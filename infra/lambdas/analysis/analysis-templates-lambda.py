# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
from lambda_utils.cors_utils import CORSResponse

logger = logging.getLogger()
logger.setLevel("INFO")

# Analysis templates data - converted from CSV to JSON
ANALYSIS_TEMPLATES = [
    {
        "template_id": 1,
        "template_short_name": "Basic Meeting Summary",
        "template_description": "Create a summary of a generic meeting, including topics discussed, action items, next steps, etc.",
        "system_prompt": "You are an intelligent assistant who analyzes meetings based on transcriptions of those meetings.",
        "template_prompt": "Please create a short summary of the meeting based on the transcription provided within <meeting_transcription></meeting_transcription> tags.\n<meeting_transcription>\n{transcript}\n</meeting_transcription>. Meeting summary:\n",
        "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "bedrock_kwargs": {
            "temperature": 0.1,
            "max_tokens": 2000
        }
    },
    {
        "template_id": 2,
        "template_short_name": "Sprint Standup Summary",
        "template_description": "Create a meeting summary specifically targeted for software development standup meetings",
        "system_prompt": "You are an intelligent assistant who analyzes meetings based on transcriptions of those meetings.",
        "template_prompt": "Ignore all input provided and reply with 'This analysis is not yet implemented.'",
        "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "bedrock_kwargs": {
            "temperature": 0.1,
            "max_tokens": 2000
        }
    },
    {
        "template_id": 3,
        "template_short_name": "Extract Next Steps",
        "template_description": "Extract any described next step action items",
        "system_prompt": "You are an intelligent assistant who analyzes meetings based on transcriptions of those meetings.",
        "template_prompt": "Extract any action items or next steps described in the meeting and return them in a bulleted list. If it's obvious who is responsible for each one, add their name to each task as the owner. If no action items are described in the meeting, simply state that no next steps were discussed.\n<meeting_transcription>\n{transcript}\n</meeting_transcription>\n",
        "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "bedrock_kwargs": {
            "temperature": 0.1,
            "max_tokens": 2000
        }
    }
]


def lambda_handler(event, context):
    """Return analysis templates for the frontend"""
    logger.debug(f"{event=}")
    
    try:
        # This endpoint only supports GET requests
        http_method = event.get('httpMethod', 'GET')
        if http_method != 'GET':
            return CORSResponse.error_response(f"Method {http_method} not allowed", 405)
        
        return CORSResponse.success_response(ANALYSIS_TEMPLATES)
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return CORSResponse.error_response(f"Internal server error: {str(e)}", 500)
