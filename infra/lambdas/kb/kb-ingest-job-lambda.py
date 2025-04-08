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

import logging
import os
# import time

import boto3

from schemas.job_status import JobStatus
from lambda_utils.invoke_lambda import invoke_lambda
from preprocessing.preprocessing_utils import (
    extract_username_from_s3_URI,
    extract_uuid_from_s3_URI,
)

KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
DATA_SOURCE_ID = os.environ["DATA_SOURCE_ID"]
AWS_REGION = os.environ["AWS_REGION"]
DDB_LAMBDA_NAME = os.environ.get("DDB_LAMBDA_NAME")
SOURCE_BUCKET = os.environ.get("S3_BUCKET")
TEXT_TRANSCRIPTS_PREFIX = os.environ.get("TEXT_TRANSCRIPTS_PREFIX")

bedrock_agent_client = boto3.client("bedrock-agent", region_name=AWS_REGION)

# Create a Lambda client so this lambda can invoke other lambdas
lambda_client = boto3.client("lambda")

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
    """Call the KB sync function, possibly sleeping and retrying a few times
    Also update the dynamo DB job status for this UUID to "Indexing"
    """

    s3_file_key = event["detail"]["object"]["key"]
    logger.info(f"Ingest lambda {s3_file_key=}")
    username = extract_username_from_s3_URI(s3_file_key)
    ddb_uuid = extract_uuid_from_s3_URI(s3_file_key)
    # Get Account ID from lambda function arn in the context
    ACCOUNT_ID = context.invoked_function_arn.split(":")[4]
    logger.info(f"Extracted account ID = {ACCOUNT_ID}")
    input_data = {
        "knowledgeBaseId": KNOWLEDGE_BASE_ID,
        "dataSourceId": DATA_SOURCE_ID,
        "documents": [
            {
                "content": {
                    "dataSourceType": "S3",
                    "s3": {
                        "s3Location": {
                            "uri": f"s3://{SOURCE_BUCKET}/{TEXT_TRANSCRIPTS_PREFIX}/{username}/{ddb_uuid}.txt"
                        }
                    },
                },
                "metadata": {
                    "s3Location": {
                        "bucketOwnerAccountId": ACCOUNT_ID,
                        "uri": f"s3://{SOURCE_BUCKET}/{TEXT_TRANSCRIPTS_PREFIX}/{username}/{ddb_uuid}.txt.metadata.json",
                    },
                    "type": "S3_LOCATION",
                },
            },
        ],
    }
    try:
        logger.info(f"Starting ingestion job with {input_data=}")
        ingest_start_response = bedrock_agent_client.ingest_knowledge_base_documents(
            **input_data
        )
        # ingest_job_id = ingest_start_response["ingestionJob"]["ingestionJobId"]
        logger.info(f"Ingestion job response: {ingest_start_response=}")
        # Update DDB status
        _ = invoke_lambda(
            lambda_client=lambda_client,
            lambda_function_name=DDB_LAMBDA_NAME,
            action="update_job_status",
            params={
                "job_id": ddb_uuid,
                "username": username,
                "new_status": JobStatus.INDEXING.value,
            },
        )

        logger.info(f"Updated job status for {ddb_uuid=} to Indexing.")

        # Return uuid and ddb_uuid fr kb-job-status-lambda to use to track job status
        return {
            # "ingestion_job_id": ingest_job_id,
            "uuid": ddb_uuid,
            "username": username,
        }

    except Exception as e:
        logger.warning(f"Exception thrown in kb-ingest-job-lambda: {e}")
        raise e
