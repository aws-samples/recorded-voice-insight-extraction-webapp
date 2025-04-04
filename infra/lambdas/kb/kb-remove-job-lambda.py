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
from lambda_utils.invoke_lambda import invoke_lambda
import boto3

KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
DATA_SOURCE_ID = os.environ["DATA_SOURCE_ID"]
AWS_REGION = os.environ["AWS_REGION"]
DDB_LAMBDA_NAME = os.environ.get("DDB_LAMBDA_NAME")
SOURCE_BUCKET = os.environ.get("S3_BUCKET")
TEXT_TRANSCRIPTS_PREFIX = os.environ.get("TEXT_TRANSCRIPTS_PREFIX")
RECORDINGS_PREFIX = os.environ.get("RECORDINGS_PREFIX")
TRANSCRIPTS_PREFIX = os.environ.get("TRANSCRIPTS_PREFIX")

bedrock_agent_client = boto3.client("bedrock-agent", region_name=AWS_REGION)
s3_client = boto3.client("s3")
# Create a Lambda client so this lambda can invoke other lambdas
lambda_client = boto3.client("lambda")

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
    """Call the KB sync function to delete files from the knowledge base
    Also delete the media and transcript files from s3, and also
    delete the row from dynamodb"""

    if "body" in event:
        event = json.loads(event["body"])

    username = event["username"]
    UUID = event["job_id"]

    input_data = {
        "knowledgeBaseId": KNOWLEDGE_BASE_ID,
        "dataSourceId": DATA_SOURCE_ID,
        "documentIdentifiers": [
            {
                "dataSourceType": "S3",
                "s3": {
                    "uri": f"s3://{SOURCE_BUCKET}/{TEXT_TRANSCRIPTS_PREFIX}/{username}/{UUID}.txt"
                },
            }
        ],
    }
    try:
        logger.info(f"Starting deletion job with {input_data=}")
        deletion_response = bedrock_agent_client.delete_knowledge_base_documents(
            **input_data
        )

        logger.info(f"Deletion job response: {deletion_response=}")

        # Note: deletion may take several seconds. It must FULLY complete (e.g.
        # deletion_response['documentDetails'][0]['status'] == 'NOT_FOUND')
        # BEFORE you delete the txt and metadata file from s3.
        # Instead of having this lambda try/retry for the deletion to complete,
        # we opt to simply never delete the txt and metadata files from s3.
        # Deleting the source media file, transcript json/vtt, and the dynamodb
        # row is sufficient for the app to have no access to the remaining
        # txt files.
        # TODO: perhaps incorporate a state machine here to do this more cleanly
        # with benefits being 1) verification that KB delete sync worked
        # successfully, and 2) total clean up of s3, no remaining artifacts

        # Retrieve media_name from ddb
        media_name = invoke_lambda(
            lambda_client=lambda_client,
            lambda_function_name=DDB_LAMBDA_NAME,
            action="retrieve_media_name_by_jobid",
            params={
                "job_id": UUID,
                "username": username,
            },
        )

        logger.info(f"Deleting from s3: {media_name=} {UUID=}")

        # Delete media and transcript files from s3
        keys_to_delete = [
            f"{RECORDINGS_PREFIX}/{username}/{media_name}",
            ## We don't delete these two files ever. See above comment block
            ## for explanation why.
            # f"{TEXT_TRANSCRIPTS_PREFIX}/{username}/{UUID}.txt",
            # f"{TEXT_TRANSCRIPTS_PREFIX}/{username}/{UUID}.txt.metadata.json",
            f"{TRANSCRIPTS_PREFIX}/{username}/{UUID}.json",
            f"{TRANSCRIPTS_PREFIX}/{username}/{UUID}.vtt",
        ]
        for key_to_delete in keys_to_delete:
            _ = s3_client.delete_object(Bucket=SOURCE_BUCKET, Key=key_to_delete)

        # Delete row from ddb
        logger.info(f"Deleting row from ddb: {username=} {UUID=}")

        _ = invoke_lambda(
            lambda_client=lambda_client,
            lambda_function_name=DDB_LAMBDA_NAME,
            action="delete_ddb_entry",
            params={
                "job_id": UUID,
                "username": username,
            },
        )
    except Exception as e:
        logger.error(f"Exception thrown in kb-ingest-job-lambda: {e}")
        return {
            "statusCode": 400,
            "body": json.dumps(f"Error in deletion for {username=} {UUID=}: {e}"),
        }
    return {
        "statusCode": 200,
        "body": json.dumps(f"Deletion for {username=} {UUID=} successful."),
    }
