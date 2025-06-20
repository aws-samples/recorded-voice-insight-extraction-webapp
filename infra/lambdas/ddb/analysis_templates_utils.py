# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Utility functions for managing analysis templates in DynamoDB
"""

import json
import logging
from typing import Dict, List, Any, Optional
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()


def _serialize_bedrock_kwargs(bedrock_kwargs: Dict[str, Any]) -> str:
    """Serialize bedrock_kwargs to JSON string for DynamoDB storage"""
    return json.dumps(bedrock_kwargs)


def _deserialize_bedrock_kwargs(bedrock_kwargs_str: str) -> Dict[str, Any]:
    """Deserialize bedrock_kwargs from JSON string"""
    try:
        return json.loads(bedrock_kwargs_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to deserialize bedrock_kwargs: {bedrock_kwargs_str}")
        return {"temperature": 0.1, "maxTokens": 2000}  # Default fallback


def _format_template_for_response(template: Dict[str, Any]) -> Dict[str, Any]:
    """Format a template from DynamoDB for API response"""
    formatted = template.copy()

    # Deserialize bedrock_kwargs if it's a string
    if isinstance(formatted.get("bedrock_kwargs"), str):
        formatted["bedrock_kwargs"] = _deserialize_bedrock_kwargs(
            formatted["bedrock_kwargs"]
        )

    return formatted


def get_templates_for_user(table, user_id: str) -> List[Dict[str, Any]]:
    """
    Get all templates available to a user (default + user-specific)

    Args:
        table: DynamoDB table resource
        user_id: User ID to get templates for

    Returns:
        List of template dictionaries
    """
    templates = []

    try:
        # Get default templates
        default_response = table.query(
            KeyConditionExpression=Key("user_id").eq("default")
        )
        default_templates = default_response.get("Items", [])

        # Get user-specific templates if user_id is not 'default'
        if user_id != "default":
            user_response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id)
            )
            user_templates = user_response.get("Items", [])
            default_templates.extend(user_templates)

        # Format templates for response
        for template in default_templates:
            formatted_template = _format_template_for_response(template)
            templates.append(formatted_template)

        logger.info(f"Retrieved {len(templates)} templates for user {user_id}")
        return templates

    except Exception as e:
        logger.error(f"Error retrieving templates for user {user_id}: {str(e)}")
        raise e


def create_user_template(
    table,
    user_id: str,
    template_id: str,
    template_short_name: str,
    template_description: str,
    system_prompt: str,
    template_prompt: str,
    model_id: str,
    bedrock_kwargs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a new user-specific template

    Args:
        table: DynamoDB table resource
        user_id: User ID who owns the template
        template_id: Unique template ID
        template_short_name: Short name for the template
        template_description: Description of what the template does
        system_prompt: System prompt for the LLM
        template_prompt: Main template prompt
        model_id: Bedrock model ID to use
        bedrock_kwargs: Additional parameters for Bedrock

    Returns:
        The created template item
    """
    try:
        item = {
            "user_id": user_id,
            "template_id": template_id,
            "template_short_name": template_short_name,
            "template_description": template_description,
            "system_prompt": system_prompt,
            "template_prompt": template_prompt,
            "model_id": model_id,
            "bedrock_kwargs": _serialize_bedrock_kwargs(bedrock_kwargs),
        }

        # Use put_item with condition to prevent overwriting
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(user_id) AND attribute_not_exists(template_id)",
        )

        logger.info(f"Created template {template_id} for user {user_id}")

        # Return formatted template for response
        return _format_template_for_response(item)

    except Exception as e:
        logger.error(
            f"Error creating template {template_id} for user {user_id}: {str(e)}"
        )
        raise e


def update_user_template(
    table, user_id: str, template_id: str, updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing user template

    Args:
        table: DynamoDB table resource
        user_id: User ID who owns the template
        template_id: Template ID to update
        updates: Dictionary of fields to update

    Returns:
        The updated template item
    """
    try:
        # Build update expression
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}

        for key, value in updates.items():
            if key in ["user_id", "template_id"]:
                continue  # Skip partition/sort keys

            attr_name = f"#{key}"
            attr_value = f":{key}"

            # Serialize bedrock_kwargs if present
            if key == "bedrock_kwargs" and isinstance(value, dict):
                value = _serialize_bedrock_kwargs(value)

            update_expression += f"{attr_name} = {attr_value}, "
            expression_attribute_names[attr_name] = key
            expression_attribute_values[attr_value] = value

        # Remove trailing comma and space
        update_expression = update_expression.rstrip(", ")

        response = table.update_item(
            Key={"user_id": user_id, "template_id": template_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW",
        )

        logger.info(f"Updated template {template_id} for user {user_id}")

        # Return formatted template for response
        return _format_template_for_response(response["Attributes"])

    except Exception as e:
        logger.error(
            f"Error updating template {template_id} for user {user_id}: {str(e)}"
        )
        raise e


def delete_user_template(table, user_id: str, template_id: str) -> bool:
    """
    Delete a user-specific template (cannot delete default templates)

    Args:
        table: DynamoDB table resource
        user_id: User ID who owns the template
        template_id: Template ID to delete

    Returns:
        True if deleted successfully
    """
    try:
        # Prevent deletion of default templates
        if user_id == "default":
            raise ValueError("Cannot delete default templates")

        table.delete_item(
            Key={"user_id": user_id, "template_id": template_id},
            ConditionExpression="attribute_exists(user_id) AND attribute_exists(template_id)",
        )

        logger.info(f"Deleted template {template_id} for user {user_id}")
        return True

    except Exception as e:
        logger.error(
            f"Error deleting template {template_id} for user {user_id}: {str(e)}"
        )
        raise e


def get_template_by_id(
    table, user_id: str, template_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a specific template by ID, checking both user-specific and default templates

    Args:
        table: DynamoDB table resource
        user_id: User ID to check for user-specific template
        template_id: Template ID to retrieve

    Returns:
        Template dictionary if found, None otherwise
    """
    try:
        # First check user-specific templates
        if user_id != "default":
            try:
                response = table.get_item(
                    Key={"user_id": user_id, "template_id": template_id}
                )
                if "Item" in response:
                    return _format_template_for_response(response["Item"])
            except Exception:
                pass  # Continue to check default templates

        # Check default templates
        try:
            response = table.get_item(
                Key={"user_id": "default", "template_id": template_id}
            )
            if "Item" in response:
                return _format_template_for_response(response["Item"])
        except Exception:
            pass

        logger.warning(f"Template {template_id} not found for user {user_id}")
        return None

    except Exception as e:
        logger.error(
            f"Error retrieving template {template_id} for user {user_id}: {str(e)}"
        )
        raise e
