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


import json
import logging
import os

import boto3
import ddb.ddb_utils as ddb_utils
import ddb.analysis_templates_utils as analysis_templates_utils
from schemas.job_status import JobStatus
from lambda_utils.cors_utils import CORSResponse

logger = logging.getLogger()
logger.setLevel("INFO")

TABLE_NAME = os.environ["DYNAMO_TABLE_NAME"]
BDA_UUID_MAP_TABLE_NAME = os.environ["BDA_MAP_DYNAMO_TABLE_NAME"]
ANALYSIS_TEMPLATES_TABLE_NAME = os.environ.get("ANALYSIS_TEMPLATES_TABLE_NAME")

dyn_resource = boto3.resource("dynamodb")
table = dyn_resource.Table(name=TABLE_NAME)
bda_uuid_map_table = dyn_resource.Table(name=BDA_UUID_MAP_TABLE_NAME)

# Analysis templates table (optional for backward compatibility)
analysis_templates_table = None
if ANALYSIS_TEMPLATES_TABLE_NAME:
    analysis_templates_table = dyn_resource.Table(name=ANALYSIS_TEMPLATES_TABLE_NAME)


def lambda_handler(event, context):
    """Call appropriate ddb_utils function based on 'action' field of event input"""
    # When this lambda is called by the frontend via API gateway, the event
    # has a 'body' key. When this lambda is called by other lambdas, this is
    # unnecessary

    logger.debug(f"{event=}")

    try:
        if "body" in event:
            event = json.loads(event["body"])

        action = event["action"]

        if action == "retrieve_all_items":
            username = event["username"]
            result = ddb_utils.retrieve_all_items(table=table, username=username)
        elif action == "update_ddb_entry":
            job_id = event["job_id"]
            username = event["username"]
            new_item_name = event["new_item_name"]
            new_item_value = event["new_item_value"]
            result = ddb_utils._update_ddb_entry(
                table=table,
                uuid=job_id,
                username=username,
                new_item_name=new_item_name,
                new_item_value=new_item_value,
            )
        elif action == "update_job_status":
            job_id = event["job_id"]
            username = event["username"]
            new_status = JobStatus(event["new_status"])
            result = ddb_utils._update_job_status(
                table=table, uuid=job_id, username=username, new_status=new_status
            )
        elif action == "create_ddb_entry":
            job_id = event["job_id"]
            media_uri = event["media_uri"]
            username = event["username"]
            result = ddb_utils._create_ddb_entry(
                table=table, uuid=job_id, media_uri=media_uri, username=username
            )
        elif action == "retrieve_media_name_by_jobid":
            job_id = event["job_id"]
            username = event["username"]
            result = ddb_utils._retrieve_media_name_by_jobid(
                table=table, job_id=job_id, username=username
            )
        elif action == "retrieve_jobid_by_media_name":
            media_name = event["media_name"]
            username = event["username"]
            result = ddb_utils._retrieve_jobid_by_media_name(
                table=table, media_name=media_name, username=username
            )
        elif action == "delete_ddb_entry":
            job_id = event["job_id"]
            username = event["username"]
            result = ddb_utils._delete_job_by_id(
                table=table, username=username, job_id=job_id
            )
            # TODO: delete from bda_mapping table if entry exists
        elif action == "store_bda_mapping":
            job_id = event["job_id"]
            bda_uuid = event["bda_uuid"]
            username = event["username"]
            result = ddb_utils._create_bda_map_entry(
                table=bda_uuid_map_table,
                bda_uuid=bda_uuid,
                job_id=job_id,
                username=username,
            )
        elif action == "retrieve_jobid_and_username_by_bda_uuid":
            bda_uuid = event["bda_uuid"]
            result = ddb_utils._retrieve_jobid_and_username_by_bda_uuid(
                table=bda_uuid_map_table, bda_uuid=bda_uuid
            )
        # Analysis Templates actions
        elif action == "get_analysis_templates":
            if not analysis_templates_table:
                return CORSResponse.error_response("Analysis templates table not configured", 500)
            user_id = event["user_id"]
            result = analysis_templates_utils.get_templates_for_user(
                table=analysis_templates_table, user_id=user_id
            )
        elif action == "create_analysis_template":
            if not analysis_templates_table:
                return CORSResponse.error_response("Analysis templates table not configured", 500)
            user_id = event["user_id"]
            template_id = event["template_id"]
            template_short_name = event["template_short_name"]
            template_description = event["template_description"]
            system_prompt = event["system_prompt"]
            template_prompt = event["template_prompt"]
            model_id = event["model_id"]
            bedrock_kwargs = event["bedrock_kwargs"]
            result = analysis_templates_utils.create_user_template(
                table=analysis_templates_table,
                user_id=user_id,
                template_id=template_id,
                template_short_name=template_short_name,
                template_description=template_description,
                system_prompt=system_prompt,
                template_prompt=template_prompt,
                model_id=model_id,
                bedrock_kwargs=bedrock_kwargs
            )
        elif action == "update_analysis_template":
            if not analysis_templates_table:
                return CORSResponse.error_response("Analysis templates table not configured", 500)
            user_id = event["user_id"]
            template_id = event["template_id"]
            updates = event["updates"]
            result = analysis_templates_utils.update_user_template(
                table=analysis_templates_table,
                user_id=user_id,
                template_id=template_id,
                updates=updates
            )
        elif action == "delete_analysis_template":
            if not analysis_templates_table:
                return CORSResponse.error_response("Analysis templates table not configured", 500)
            user_id = event["user_id"]
            template_id = event["template_id"]
            result = analysis_templates_utils.delete_user_template(
                table=analysis_templates_table,
                user_id=user_id,
                template_id=template_id
            )
        elif action == "get_analysis_template_by_id":
            if not analysis_templates_table:
                return CORSResponse.error_response("Analysis templates table not configured", 500)
            user_id = event["user_id"]
            template_id = event["template_id"]
            result = analysis_templates_utils.get_template_by_id(
                table=analysis_templates_table,
                user_id=user_id,
                template_id=template_id
            )
        else:
            return CORSResponse.error_response("Invalid action", 400)

        return CORSResponse.success_response(result)
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return CORSResponse.error_response(f"Internal server error: {str(e)}", 500)
