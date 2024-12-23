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

bedrock_agent_client = boto3.client("bedrock-agent", region_name=AWS_REGION)
# Create a Lambda client so this lambda can invoke other lambdas
lambda_client = boto3.client("lambda")

logger = logging.getLogger()
logger.setLevel("DEBUG")


def lambda_handler(event, context):
    # This gets passed in from the previous lambda in the state machine, which launches sync job
    ingestion_job_id = event["ingestion_job_id"]

    try:
        ingest_status_response = bedrock_agent_client.get_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
            ingestionJobId=ingestion_job_id,
        )

        job_status = ingest_status_response["ingestionJob"]["status"]
        logger.debug(f"Ingestion job status: {job_status}")

        # Possible Bedrock knowledge base sync job statuses:
        # "STARTING" | "IN_PROGRESS" | "COMPLETE" | "FAILED" | "STOPPING" | "STOPPED"

        # If job is complete or failed, update dynamoDB
        if job_status == "COMPLETE":
            _ = invoke_lambda(
                lambda_client=lambda_client,
                lambda_function_name=DDB_LAMBDA_NAME,
                action="batch_update_job_statuses",
                params={
                    "ingestion_job_id": ingestion_job_id,
                    "new_status": JobStatus.COMPLETED.value,
                },
            )
        elif job_status == "FAILED":
            _ = invoke_lambda(
                lambda_client=lambda_client,
                lambda_function_name=DDB_LAMBDA_NAME,
                action="batch_update_job_statuses",
                params={
                    "ingestion_job_id": ingestion_job_id,
                    "new_status": JobStatus.FAILED.value,
                },
            )
        # Return the job status regardless
        # how does this response get used by the state machine with "$.Payload"
        return {"status": job_status, "ingestion_job_id": ingestion_job_id}

    except Exception as e:
        logger.warning(f"Error checking job status: {str(e)}")
        raise
