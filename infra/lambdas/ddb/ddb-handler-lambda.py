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
import boto3
import ddb.ddb_utils as ddb_utils
from schemas.job_status import JobStatus
import os
import logging

logger = logging.getLogger()
logger.setLevel("DEBUG")

TABLE_NAME = os.environ["DYNAMO_TABLE_NAME"]
dyn_resource = boto3.resource("dynamodb")
table = dyn_resource.Table(name=TABLE_NAME)


def lambda_handler(event, context):
    """Call appropriate ddb_utils function based on 'action' field of event input"""
    # When this lambda is called by the frontend via API gateway, the event
    # has a 'body' key. When this lambda is called by other lambdas, this is
    # unnecessary

    logger.debug(f"{event=}")

    if "body" in event:
        event = json.loads(event["body"])

    action = event["action"]

    if action == "retrieve_all_items":
        username = event["username"]
        result = ddb_utils.retrieve_all_items(table=table, username=username)
    elif action == "retrieve_analysis_by_jobid":
        job_id = event["job_id"]
        username = event["username"]
        template_id = event["template_id"]
        result = ddb_utils.retrieve_analysis_by_jobid(
            table=table, job_id=job_id, username=username, template_id=template_id
        )
    elif action == "store_analysis_result":
        job_id = event["job_id"]
        username = event["username"]
        template_id = event["template_id"]
        analysis_result = event["analysis_result"]
        ddb_utils.store_analysis_result(
            table=table,
            job_id=job_id,
            username=username,
            template_id=template_id,
            analysis_result=analysis_result,
        )
        result = "Analysis stored successfully"
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
    elif action == "batch_update_job_statuses":
        ingestion_job_id = event["ingestion_job_id"]
        new_status = JobStatus(event["new_status"])
        result = ddb_utils._batch_update_job_statuses(
            table=table, ingestion_job_id=ingestion_job_id, new_status=new_status
        )
    else:
        return {"statusCode": 400, "body": json.dumps("Invalid action")}

    return {"statusCode": 200, "body": json.dumps(result)}
