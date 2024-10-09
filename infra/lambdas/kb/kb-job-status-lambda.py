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
from ddb.ddb_utils import batch_update_job_statuses

KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
DYNAMO_TABLE_NAME = os.environ["DYNAMO_TABLE_NAME"]
AWS_REGION = os.environ["AWS_REGION"]
DATA_SOURCE_ID = os.environ["DATA_SOURCE_ID"]

bedrock_agent_client = boto3.client("bedrock-agent", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMO_TABLE_NAME)

logger = logging.getLogger()
logger.setLevel("DEBUG")


def lambda_handler(event, context):
    # This gets passed in from the previous lambda in the state machine, which launches sync job
    ingestion_job_id = event["ingestion_job_id"]

    try:
        response = bedrock_agent_client.get_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
            ingestionJobId=ingestion_job_id,
        )

        job_status = response["ingestionJob"]["status"]
        logger.debug(f"Ingestion job status: {job_status}")

        if job_status == "COMPLETED":
            batch_update_job_statuses(table, ingestion_job_id, "Complete")
        elif job_status == "FAILED":
            batch_update_job_statuses(table, ingestion_job_id, "Failed")

        return {"status": job_status, "ingestion_job_id": ingestion_job_id}

    except Exception as e:
        logger.error(f"Error checking job status: {str(e)}")
        raise
