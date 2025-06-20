# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
import os
import boto3
from boto3.dynamodb.conditions import Key
from lambda_utils.cors_utils import CORSResponse

logger = logging.getLogger()
logger.setLevel("INFO")

ANALYSIS_TEMPLATES_TABLE_NAME = os.environ["ANALYSIS_TEMPLATES_TABLE_NAME"]
dynamodb = boto3.resource("dynamodb")
analysis_templates_table = dynamodb.Table(ANALYSIS_TEMPLATES_TABLE_NAME)


def lambda_handler(event, context):
    """Return analysis templates for the frontend from DynamoDB"""
    logger.debug(f"{event=}")

    try:
        # This endpoint only supports GET requests
        http_method = event.get("httpMethod", "GET")
        if http_method != "GET":
            return CORSResponse.error_response(f"Method {http_method} not allowed", 405)

        # Get username from the request (from Cognito JWT token)
        username = None
        if "requestContext" in event and "authorizer" in event["requestContext"]:
            claims = event["requestContext"]["authorizer"].get("claims", {})
            username = claims.get("cognito:username")

        if not username:
            logger.warning("No username found in request context")
            username = "unknown"

        templates = []

        # Get default templates (available to all users)
        try:
            default_response = analysis_templates_table.query(
                KeyConditionExpression=Key("user_id").eq("default")
            )
            default_templates = default_response.get("Items", [])

            # Convert DynamoDB items to the expected format
            for template in default_templates:
                formatted_template = {
                    "template_id": template["template_id"],
                    "template_short_name": template["template_short_name"],
                    "template_description": template["template_description"],
                    "system_prompt": template.get("system_prompt", ""),
                    "template_prompt": template["template_prompt"],
                    "model_id": template.get(
                        "model_id", "anthropic.claude-3-sonnet-20240229-v1:0"
                    ),
                    "bedrock_kwargs": template.get(
                        "bedrock_kwargs", {"temperature": 0.1, "max_tokens": 2000}
                    ),
                }
                templates.append(formatted_template)

            logger.info(f"Retrieved {len(default_templates)} default templates")

        except Exception as e:
            logger.error(f"Error retrieving default templates: {str(e)}")

        # Get user-specific templates
        try:
            user_response = analysis_templates_table.query(
                KeyConditionExpression=Key("user_id").eq(username)
            )
            user_templates = user_response.get("Items", [])

            # Convert DynamoDB items to the expected format
            for template in user_templates:
                formatted_template = {
                    "template_id": template["template_id"],
                    "template_short_name": template["template_short_name"],
                    "template_description": template["template_description"],
                    "system_prompt": template.get("system_prompt", ""),
                    "template_prompt": template["template_prompt"],
                    "model_id": template.get(
                        "model_id", "anthropic.claude-3-sonnet-20240229-v1:0"
                    ),
                    "bedrock_kwargs": template.get(
                        "bedrock_kwargs", {"temperature": 0.1, "max_tokens": 2000}
                    ),
                }
                templates.append(formatted_template)

            logger.info(
                f"Retrieved {len(user_templates)} user-specific templates for user: {username}"
            )

        except Exception as e:
            logger.error(f"Error retrieving user templates for {username}: {str(e)}")

        logger.info(f"Returning {len(templates)} total templates")
        return CORSResponse.success_response(templates)

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return CORSResponse.error_response(f"Internal server error: {str(e)}", 500)
