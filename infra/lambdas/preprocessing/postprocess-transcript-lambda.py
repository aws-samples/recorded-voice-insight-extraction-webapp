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
from preprocessing.preprocessing_utils import (
    extract_username_from_s3_URI,
    build_timestamped_segmented_transcript,
    build_kb_metadata_json,
)
from ddb.ddb_utils import (
    update_ddb_entry,
    update_job_status,
    retrieve_media_name_by_jobid,
)

logger = logging.getLogger()
logger.setLevel("DEBUG")

S3_BUCKET = os.environ.get("S3_BUCKET")
SOURCE_PREFIX = os.environ.get("SOURCE_PREFIX")
DESTINATION_PREFIX = os.environ.get("DESTINATION_PREFIX")
DYNAMO_TABLE_NAME = os.environ.get("DYNAMO_TABLE_NAME")

s3 = boto3.client("s3")
ddb_table = boto3.resource("dynamodb").Table(name=DYNAMO_TABLE_NAME)


def lambda_handler(event, context):
    """Convert json to txt, write txt and metadata to s3, and also log to dynamodb"""
    logger.debug("postprocess-transcript-lambda handler called.")
    logger.debug(f"{event=}")
    logger.debug(f"{context=}")

    # Read in json file, dump to txt
    json_transcript_key = event["Records"][0]["s3"]["object"]["key"]
    logger.debug(f"{json_transcript_key=}")
    username = extract_username_from_s3_URI(json_transcript_key)
    logger.debug(f"{username=}")
    filename = os.path.split(json_transcript_key)[1]
    uuid, extension = os.path.splitext(filename)
    try:
        assert extension == ".json"
    except AssertionError as err:
        logger.warning(f"Unable to dump txt from non-json file: {json_transcript_key}.")
        raise err

    output_key = os.path.join(DESTINATION_PREFIX, username, uuid + ".txt")
    logger.debug(f"{output_key=}")

    try:
        # Download json_uri from s3 to tmp dir, read it in
        full_json = json.loads(
            s3.get_object(Bucket=S3_BUCKET, Key=json_transcript_key)["Body"]
            .read()
            .decode()
        )

        # Save json URI to dynamodb
        response = update_ddb_entry(
            table=ddb_table,
            uuid=uuid,
            username=username,
            new_item_name="json_transcript_uri",
            new_item_value=os.path.join("s3://", S3_BUCKET, json_transcript_key),
        )
        logger.debug(f"Response to putting json URI into {uuid}: {response}")

        # Convert json transcript into human readable form for LLM
        transcript_processed = build_timestamped_segmented_transcript(full_json)

        # Build json with metadata for Bedrock KB to index and filter on later
        # Note: need to get media_uri from DDB
        media_name = retrieve_media_name_by_jobid(
            table=ddb_table,
            job_id=uuid,
            username=username,
        )
        meta_json = build_kb_metadata_json(username=username, media_name=media_name)

        # Save txt URI to dynamodb
        response = update_ddb_entry(
            table=ddb_table,
            uuid=uuid,
            username=username,
            new_item_name="txt_transcript_uri",
            new_item_value=os.path.join("s3://", S3_BUCKET, output_key),
        )
        logger.debug(f"Response to putting text uri into {uuid}: {response}")

        # Upload transcript to s3 as a text file
        put_response = s3.put_object(
            Body=bytes(transcript_processed, "utf-8"), Bucket=S3_BUCKET, Key=output_key
        )
        logger.debug(f"Response to putting text into s3: {put_response}")

        # Upload metadata to s3 as a json file
        # of form blahblah.txt.metadata.json (required by Bedrock KB)
        metadata_output_key = output_key + ".metadata.json"
        put_response = s3.put_object(
            Body=bytes(json.dumps(meta_json, indent=2), "utf-8"),
            Bucket=S3_BUCKET,
            Key=metadata_output_key,
        )
        logger.debug(f"Response to putting text into s3: {put_response}")

    except Exception as e:
        logger.warning(f"ERROR Exception caught in postprocess-transcript-lambda: {e}.")
        # Update job status in dynamodb
        update_job_status(
            table=ddb_table,
            uuid=uuid,
            username=username,
            new_status="Failed",
        )
        raise

    # Update job status in dynamodb
    update_job_status(
        table=ddb_table,
        uuid=uuid,
        username=username,
        new_status="Transcription Complete",
    )

    return {
        "statusCode": 200,
        "body": json.dumps("postprocess-transcript routine complete."),
    }
