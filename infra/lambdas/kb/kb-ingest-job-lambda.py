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
import time

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

bedrock_agent_client = boto3.client("bedrock-agent", region_name=AWS_REGION)

# Create a Lambda client so this lambda can invoke other lambdas
lambda_client = boto3.client("lambda")

logger = logging.getLogger()
logger.setLevel("DEBUG")


# Structured this way to fix Probe scan issues
def sleep_dur():
    return 60


def lambda_handler(event, context):
    """Call the KB sync function, possibly sleeping and retrying a few times
    Also update the dynamo DB job status for this UUID to "Indexing"
    """
    input_data = {
        "knowledgeBaseId": KNOWLEDGE_BASE_ID,
        "dataSourceId": DATA_SOURCE_ID,
        # "clientToken": context.aws_request_id,
    }
    s3_file_key = event["detail"]["object"]["key"]
    logger.debug(f"Ingest lambda {s3_file_key=}")
    username = extract_username_from_s3_URI(s3_file_key)
    ddb_uuid = extract_uuid_from_s3_URI(s3_file_key)

    # Retry a few times
    # TODO: handle this better with a queue or something
    response = None
    retries_left = 5
    while response is None:
        try:
            logger.debug(f"Starting ingestion job with {input_data=}")
            ingest_start_response = bedrock_agent_client.start_ingestion_job(
                **input_data
            )
            ingest_job_id = ingest_start_response["ingestionJob"]["ingestionJobId"]
            logger.debug(f"Ingestion job response: {ingest_start_response=}")
            # Update DDB status
            response = invoke_lambda(
                lambda_client=lambda_client,
                lambda_function_name=DDB_LAMBDA_NAME,
                action="update_job_status",
                params={
                    "job_id": ddb_uuid,
                    "username": username,
                    "new_status": JobStatus.INDEXING.value,
                },
            )

            logger.debug(f"Updated job status for {ddb_uuid=} to Indexing.")
            # Add ingestion job ID to DDB to check ingestion status later
            response = invoke_lambda(
                lambda_client=lambda_client,
                lambda_function_name=DDB_LAMBDA_NAME,
                action="update_ddb_entry",
                params={
                    "job_id": ddb_uuid,
                    "username": username,
                    "new_item_name": "ingestion_job_id",
                    "new_item_value": ingest_job_id,
                },
            )
            logger.debug(
                f"Updated DDB entry {ddb_uuid=} by adding an ingestion_job_id field, with value {ingest_job_id=}."
            )
            # Return the ingestion job ID rather than relying on downstream lambdas to read it from dynamo
            # due to potential consistency issues
            return {
                "ingestion_job_id": ingest_job_id,
                "uuid": ddb_uuid,
                "username": username,
            }

        except Exception as e:
            # E.g. too many ingestion jobs to the same KB will raise a
            # botocore.errorfactory.ConflictException
            retries_left -= 1
            if retries_left:
                response = None
                logger.debug(
                    f"Ingestion job failed with exception: {e}... retrying in 1 min"
                )
                time.sleep(sleep_dur())
            else:
                logger.debug(
                    f"Ingestion job failed and no retries left. Marking {ddb_uuid=} as Failed."
                )
                response = invoke_lambda(
                    lambda_client=lambda_client,
                    lambda_function_name=DDB_LAMBDA_NAME,
                    action="update_job_status",
                    params={
                        "job_id": ddb_uuid,
                        "username": username,
                        "new_status": JobStatus.FAILED.value,
                    },
                )

                raise e
