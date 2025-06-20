# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import boto3
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel("INFO")

ANALYSIS_TEMPLATES_TABLE_NAME = os.environ["ANALYSIS_TEMPLATES_TABLE_NAME"]
dynamodb = boto3.resource("dynamodb")
analysis_templates_table = dynamodb.Table(ANALYSIS_TEMPLATES_TABLE_NAME)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Custom resource Lambda to populate default analysis templates.
    This is called during CDK deployment to seed the DynamoDB table.
    """
    logger.info(f"Event: {json.dumps(event)}")
    
    request_type = event.get('RequestType')
    
    if request_type == 'Create' or request_type == 'Update':
        try:
            # Load default templates from the JSON file in the Lambda layer
            # Lambda layers put files in /opt/python/ for Python layers
            templates_file_path = '/opt/default_analysis_templates.json'
            
            # Try multiple possible paths where the file might be located
            possible_paths = [
                '/opt/default_analysis_templates.json',
                '/opt/python/default_analysis_templates.json',
                './default_analysis_templates.json',
                '/var/task/default_analysis_templates.json'
            ]
            
            default_templates = None
            for path in possible_paths:
                try:
                    if os.path.exists(path):
                        logger.info(f"Found templates file at: {path}")
                        with open(path, 'r') as f:
                            default_templates = json.load(f)
                        break
                except Exception as e:
                    logger.debug(f"Could not read from {path}: {str(e)}")
                    continue
            
            if not default_templates:
                raise FileNotFoundError("Could not find default_analysis_templates.json in any expected location")
            
            logger.info(f"Loaded {len(default_templates)} default templates from JSON file")
            
            # Insert default templates with user_id = "default"
            for template in default_templates:
                item = {
                    "user_id": "default",
                    "template_id": template["template_id"],
                    "template_short_name": template["template_short_name"],
                    "template_description": template["template_description"],
                    "system_prompt": template["system_prompt"],
                    "template_prompt": template["template_prompt"],
                    "model_id": template["model_id"],
                    "bedrock_kwargs": json.dumps(template["bedrock_kwargs"])  # Serialize as JSON string
                }
                
                # Use put_item with condition to avoid overwriting existing templates
                try:
                    analysis_templates_table.put_item(
                        Item=item,
                        ConditionExpression="attribute_not_exists(user_id) AND attribute_not_exists(template_id)"
                    )
                    logger.info(f"Inserted default template: {template['template_id']}")
                except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
                    logger.info(f"Default template {template['template_id']} already exists, skipping")
            
            logger.info("Successfully populated default analysis templates")
            
        except Exception as e:
            logger.error(f"Error populating default templates: {str(e)}")
            raise e
    
    elif request_type == 'Delete':
        # Optionally clean up default templates on stack deletion
        logger.info("Delete request - keeping default templates for potential reuse")
    
    # Return success response for CloudFormation
    return {
        'Status': 'SUCCESS',
        'PhysicalResourceId': 'default-templates-populator',
        'Data': {
            'Message': 'Default analysis templates populated successfully'
        }
    }
