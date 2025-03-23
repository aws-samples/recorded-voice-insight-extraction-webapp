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

import os
import logging
import boto3
from schemas.job_status import JobStatus
from lambda_utils.invoke_lambda import invoke_lambda

KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
DDB_LAMBDA_NAME = os.environ.get("DDB_LAMBDA_NAME")
AWS_REGION = os.environ["AWS_REGION"]
DATA_SOURCE_ID = os.environ["DATA_SOURCE_ID"]
SOURCE_BUCKET = os.environ.get("S3_BUCKET")
TEXT_TRANSCRIPTS_PREFIX = os.environ.get("TEXT_TRANSCRIPTS_PREFIX")

bedrock_agent_client = boto3.client("bedrock-agent", region_name=AWS_REGION)
# Create a Lambda client so this lambda can invoke other lambdas
lambda_client = boto3.client("lambda")

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
    # This gets passed in from the previous lambda in the state machine, which launches sync job
    ddb_uuid = event["uuid"]
    username = event["username"]

    try:
        ingest_status_response = bedrock_agent_client.get_knowledge_base_documents(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
            documentIdentifiers=[
                {
                    "dataSourceType": "S3",
                    "s3": {
                        "uri": f"s3://{SOURCE_BUCKET}/{TEXT_TRANSCRIPTS_PREFIX}/{username}/{ddb_uuid}.txt"
                    },
                }
            ],
        )

        job_status = ingest_status_response["documentDetails"][0]["status"]
        logger.info(f"Ingestion job status: {job_status}")

        # Possible Bedrock knowledge base sync job statuses:
        # 'INDEXED'|'PARTIALLY_INDEXED'|'PENDING'|'FAILED'|'METADATA_PARTIALLY_INDEXED'|'METADATA_UPDATE_FAILED'|'IGNORED'|'NOT_FOUND'|'STARTING'|'IN_PROGRESS'|'DELETING'|'DELETE_IN_PROGRESS'
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent/client/get_knowledge_base_documents.html

        # If job is complete or failed, update dynamoDB
        if job_status == "INDEXED":
            _ = invoke_lambda(
                lambda_client=lambda_client,
                lambda_function_name=DDB_LAMBDA_NAME,
                action="update_job_status",
                params={
                    "job_id": ddb_uuid,
                    "username": username,
                    "new_status": JobStatus.COMPLETED.value,
                },
            )
        elif job_status == "FAILED":
            _ = invoke_lambda(
                lambda_client=lambda_client,
                lambda_function_name=DDB_LAMBDA_NAME,
                action="update_job_status",
                params={
                    "job_id": ddb_uuid,
                    "username": username,
                    "new_status": JobStatus.FAILED.value,
                },
            )
        # Return the job status regardless

        # "status" is tracked by the state machine like this:
        #     .when(sfn.Condition.string_equals("$.status", "FAILED"), job_failed)
        #     .when(sfn.Condition.string_equals("$.status", "COMPLETE"), job_succeeded)
        return {
            "status": job_status,
            "uuid": ddb_uuid,
            "username": username,
        }

    except Exception as e:
        logger.warning(f"Error checking job status: {str(e)}")
        raise
