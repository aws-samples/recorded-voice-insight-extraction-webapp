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

from ddb.ddb_utils import (
    update_ddb_entry,
    update_job_status,
)
from preprocessing.preprocessing_utils import (
    extract_username_from_s3_URI,
    extract_uuid_from_s3_URI,
)

KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
DATA_SOURCE_ID = os.environ["DATA_SOURCE_ID"]
AWS_REGION = os.environ["AWS_REGION"]
DYNAMO_TABLE_NAME = os.environ.get("DYNAMO_TABLE_NAME")

ddb_table = boto3.resource("dynamodb").Table(name=DYNAMO_TABLE_NAME)

bedrock_agent_client = boto3.client("bedrock-agent", region_name=AWS_REGION)


logger = logging.getLogger()
logger.setLevel("DEBUG")


def lambda_handler(event, context):
    """Call the KB sync function, possibly sleeping and retrying a few times
    Also update the dynamo DB job status for this UUID to "Indexing"
    """
    input_data = {
        "knowledgeBaseId": KNOWLEDGE_BASE_ID,
        "dataSourceId": DATA_SOURCE_ID,
        # "clientToken": context.aws_request_id,
    }
    s3_file_key = event["Records"][0]["s3"]["object"]["key"]
    logger.debug(f"Ingest lambda {s3_file_key=}")
    username = extract_username_from_s3_URI(s3_file_key)
    job_id = extract_uuid_from_s3_URI(s3_file_key)

    # Retry a few times
    # TODO: handle this better with a queue or something
    response = None
    retries_left = 3
    while response is None:
        try:
            logger.debug(f"Starting ingestion job with {input_data=}")
            response = bedrock_agent_client.start_ingestion_job(**input_data)
            logger.debug(f"Ingestion job response: {response=}")
            # Update DDB status
            # TODO:
            update_job_status(
                table=ddb_table,
                uuid=job_id,
                username=username,
                new_status="Indexing",
            )
            # Add ingestion job ID to DDB to check ingestion status later
            update_ddb_entry(
                table=ddb_table,
                uuid=job_id,
                username=username,
                new_item_name="ingestion_job_id",
                new_item_value=response["ingestionJob"]["ingestionJobId"],
            )
            # Return the ingestion job ID rather than relying on downstream lambdas to read it from dynamo
            # due to potential consistency issues
            return {
                "ingestion_job_id": response["ingestionJob"]["ingestionJobId"],
                "uuid": job_id,
                "username": username,
            }

        except Exception as e:
            # E.g. too many ingestion jobs to the same KB will raise a
            # botocore.errorfactory.ConflictException
            retries_left -= 1
            if retries_left:
                response = None
                logger.debug(
                    f"Ingestion job failed with exception: {e}... retrying in 5 sec"
                )
                time.sleep(5)
            else:
                logger.debug(
                    "Ingestion job failed and no retries left. Marking {uuid=} as Failed."
                )
                update_job_status(
                    table=ddb_table,
                    uuid=job_id,
                    username=username,
                    new_status="Failed",
                )
                raise e
