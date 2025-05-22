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
from botocore.exceptions import ClientError

KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
DDB_LAMBDA_NAME = os.environ.get("DDB_LAMBDA_NAME")
AWS_REGION = os.environ["AWS_REGION"]
DATA_SOURCE_ID = os.environ["DATA_SOURCE_ID"]
SOURCE_BUCKET = os.environ.get("S3_BUCKET")
TEXT_TRANSCRIPTS_PREFIX = os.environ.get("TEXT_TRANSCRIPTS_PREFIX")

bedrock_agent_client = boto3.client("bedrock-agent", region_name=AWS_REGION)
# Create a Lambda client so this lambda can invoke other lambdas
lambda_client = boto3.client("lambda")
# This is just used to check if a transcript file in s3 is empty
s3_client = boto3.client("s3")

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
    # This gets passed in from the previous lambda in the state machine, which launches sync job
    ddb_uuid = event["uuid"]
    username = event["username"]
    transcript_txt_file_uri = (
        f"s3://{SOURCE_BUCKET}/{TEXT_TRANSCRIPTS_PREFIX}/{username}/{ddb_uuid}.txt"
    )
    try:
        ingest_status_response = bedrock_agent_client.get_knowledge_base_documents(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
            documentIdentifiers=[
                {
                    "dataSourceType": "S3",
                    "s3": {"uri": transcript_txt_file_uri},
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
        # Special case, transcript is empty (video file with no audio) so ingestion into KB will fail,
        # but with BDA this entire file shouldn't be considered "failed"
        elif is_s3_file_empty(transcript_txt_file_uri):
            _ = invoke_lambda(
                lambda_client=lambda_client,
                lambda_function_name=DDB_LAMBDA_NAME,
                action="update_job_status",
                params={
                    "job_id": ddb_uuid,
                    "username": username,
                    "new_status": JobStatus.BDA_PROCESSING_COMPLETE.value,
                },
            )
            job_status = "INDEXED"  # Not actually indexed, marking this variable to have state machine continue
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
        #     .when(sfn.Condition.string_equals("$.status", "INDEXED"), job_succeeded)
        return {
            "status": job_status,
            "uuid": ddb_uuid,
            "username": username,
        }

    except Exception as e:
        logger.warning(f"Error checking job status: {str(e)}")
        raise


def is_s3_file_empty(s3_uri):
    parts = s3_uri.replace("s3://", "").split("/", 1)
    bucket_name = parts[0]
    object_key = parts[1]
    # Get object metadata
    response = s3_client.head_object(Bucket=bucket_name, Key=object_key)

    # Check the Content-Length
    content_length = response["ContentLength"]
    return content_length == 0
