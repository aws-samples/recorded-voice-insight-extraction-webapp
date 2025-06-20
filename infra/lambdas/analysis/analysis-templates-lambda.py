# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import uuid
import boto3
from lambda_utils.cors_utils import CORSResponse
from ddb.analysis_templates_utils import (
    get_templates_for_user,
    create_user_template,
    update_user_template,
    delete_user_template,
    get_template_by_id,
)

logger = logging.getLogger()
logger.setLevel("INFO")

ANALYSIS_TEMPLATES_TABLE_NAME = os.environ["ANALYSIS_TEMPLATES_TABLE_NAME"]
dynamodb = boto3.resource("dynamodb")
analysis_templates_table = dynamodb.Table(ANALYSIS_TEMPLATES_TABLE_NAME)


def get_username_from_event(event):
    """Extract username from Cognito JWT token in the event"""
    username = None
    if "requestContext" in event and "authorizer" in event["requestContext"]:
        claims = event["requestContext"]["authorizer"].get("claims", {})
        username = claims.get("cognito:username")

    if not username:
        logger.warning("No username found in request context")
        raise ValueError("Authentication required")

    return username


def handle_get_templates(event, context):
    """Handle GET request to retrieve all templates for a user"""
    try:
        username = get_username_from_event(event)
        templates = get_templates_for_user(analysis_templates_table, username)

        logger.info(f"Returning {len(templates)} templates for user {username}")
        return CORSResponse.success_response(templates)

    except ValueError as e:
        return CORSResponse.error_response(str(e), 401)
    except Exception as e:
        logger.error(f"Error retrieving templates: {str(e)}")
        return CORSResponse.error_response(f"Internal server error: {str(e)}", 500)


def handle_create_template(event, context):
    """Handle POST request to create a new user template"""
    try:
        username = get_username_from_event(event)

        # Parse request body
        if not event.get("body"):
            return CORSResponse.error_response("Request body is required", 400)

        try:
            body = json.loads(event["body"])
        except json.JSONDecodeError:
            return CORSResponse.error_response("Invalid JSON in request body", 400)

        # Validate required fields
        required_fields = [
            "template_short_name",
            "template_description",
            "template_prompt",
        ]
        for field in required_fields:
            if not body.get(field):
                return CORSResponse.error_response(
                    f"Missing required field: {field}", 400
                )

        # Generate unique template ID
        template_id = str(uuid.uuid4())

        # Set defaults for optional fields
        system_prompt = body.get("system_prompt", "")
        if not system_prompt.strip():
            system_prompt = "You are an intelligent assistant who analyzes transcripts and other information extracted from audio and video files."

        # Get model_id from config or use default
        model_id = body.get("model_id", "")
        if not model_id.strip():
            # Try to get from environment variable set by CDK from config.yaml
            model_id = os.environ.get("LLM_MODEL_ID", "us.amazon.nova-pro-v1:0")

        bedrock_kwargs = body.get(
            "bedrock_kwargs", {"temperature": 0.1, "maxTokens": 2000}
        )

        # Create the template
        template = create_user_template(
            analysis_templates_table,
            username,
            template_id,
            body["template_short_name"],
            body["template_description"],
            system_prompt,
            body["template_prompt"],
            model_id,
            bedrock_kwargs,
        )

        logger.info(f"Created template {template_id} for user {username}")
        return CORSResponse.success_response(template)

    except ValueError as e:
        return CORSResponse.error_response(str(e), 401)
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        if "ConditionalCheckFailedException" in str(e):
            return CORSResponse.error_response("Template already exists", 409)
        return CORSResponse.error_response(f"Internal server error: {str(e)}", 500)


def handle_update_template(event, context):
    """Handle PUT request to update an existing user template"""
    try:
        username = get_username_from_event(event)

        # Get template_id from path parameters
        path_parameters = event.get("pathParameters", {})
        template_id = path_parameters.get("template_id")

        if not template_id:
            return CORSResponse.error_response("template_id is required in path", 400)

        # Parse request body
        if not event.get("body"):
            return CORSResponse.error_response("Request body is required", 400)

        try:
            body = json.loads(event["body"])
        except json.JSONDecodeError:
            return CORSResponse.error_response("Invalid JSON in request body", 400)

        # Check if template exists and belongs to user (not default)
        existing_template = get_template_by_id(
            analysis_templates_table, username, template_id
        )
        if not existing_template:
            return CORSResponse.error_response("Template not found", 404)

        # Prevent updating default templates
        if existing_template.get("user_id") == "default":
            return CORSResponse.error_response("Cannot update default templates", 403)

        # Update the template
        template = update_user_template(
            analysis_templates_table, username, template_id, body
        )

        logger.info(f"Updated template {template_id} for user {username}")
        return CORSResponse.success_response(template)

    except ValueError as e:
        return CORSResponse.error_response(str(e), 401)
    except Exception as e:
        logger.error(f"Error updating template: {str(e)}")
        return CORSResponse.error_response(f"Internal server error: {str(e)}", 500)


def handle_delete_template(event, context):
    """Handle DELETE request to delete a user template"""
    try:
        username = get_username_from_event(event)

        # Get template_id from path parameters
        path_parameters = event.get("pathParameters", {})
        template_id = path_parameters.get("template_id")

        if not template_id:
            return CORSResponse.error_response("template_id is required in path", 400)

        # Check if template exists and belongs to user (not default)
        existing_template = get_template_by_id(
            analysis_templates_table, username, template_id
        )
        if not existing_template:
            return CORSResponse.error_response("Template not found", 404)

        # Prevent deleting default templates
        if existing_template.get("user_id") == "default":
            return CORSResponse.error_response("Cannot delete default templates", 403)

        # Delete the template
        delete_user_template(analysis_templates_table, username, template_id)

        logger.info(f"Deleted template {template_id} for user {username}")
        return CORSResponse.success_response(
            {"message": "Template deleted successfully"}
        )

    except ValueError as e:
        return CORSResponse.error_response(str(e), 401)
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        return CORSResponse.error_response(f"Internal server error: {str(e)}", 500)


def lambda_handler(event, context):
    """Handle CRUD operations for analysis templates"""
    logger.debug(f"{event=}")

    try:
        http_method = event.get("httpMethod", "GET")

        if http_method == "GET":
            return handle_get_templates(event, context)
        elif http_method == "POST":
            return handle_create_template(event, context)
        elif http_method == "PUT":
            return handle_update_template(event, context)
        elif http_method == "DELETE":
            return handle_delete_template(event, context)
        else:
            return CORSResponse.error_response(f"Method {http_method} not allowed", 405)

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return CORSResponse.error_response(f"Internal server error: {str(e)}", 500)
