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
    build_kb_metadata_json,
    build_simplified_bda_video_string,
)
from lambda_utils.vtt_utils import (
    build_timestamped_segmented_transcript,
    bda_output_to_vtt,
)
from lambda_utils.invoke_lambda import invoke_lambda

from schemas.job_status import JobStatus

logger = logging.getLogger()
logger.setLevel("INFO")

S3_BUCKET = os.environ.get("S3_BUCKET")
DESTINATION_PREFIX = os.environ.get("DESTINATION_PREFIX")
BDA_DESTINATION_PREFIX = os.environ.get("BDA_DESTINATION_PREFIX")
VTT_DESTINATION_PREFIX = os.environ.get("VTT_DESTINATION_PREFIX")
DDB_LAMBDA_NAME = os.environ.get("DDB_LAMBDA_NAME")

s3 = boto3.client("s3")

# Create a Lambda client so this lambda can invoke other lambdas
lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    """Convert bda json to vtt (transcript), txt (simplified transcript), txt (extracted from video),
    write txt and metadata to s3, and also log to dynamodb"""
    logger.debug("postprocess-bda-lambda handler called.")
    logger.debug(f"{event=}")
    logger.debug(f"{context=}")

    # Read in json file created by bda
    # This will be under a user-agnostic prefix, and will have a UUID assigned to
    # it by BDA, which is different from the ReVIEW app job-id.
    # Therefore we have to use DDB to map this key to a user name and job id
    # bda_json_key looks like
    # some/prefix/bda-uuid/0/standard_output/0/result.json
    
    # URL-decode the S3 object key from the event notification
    # S3 event notifications URL-encode special characters in object keys.
    # We decode the key for consistency with other S3 event handlers and to ensure
    # proper handling when usernames with special characters are retrieved from DDB
    # and used in subsequent file operations.
    import urllib.parse
    bda_json_key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"])
    logger.info(f"Processing BDA output: {bda_json_key}")
    bda_uuid = bda_json_key.split("/")[-5]
    logger.debug(f"{bda_uuid=}")

    # Get username and ReVIEW job-id from DDB
    job_id, username = invoke_lambda(
        lambda_client=lambda_client,
        lambda_function_name=DDB_LAMBDA_NAME,
        action="retrieve_jobid_and_username_by_bda_uuid",
        params={"bda_uuid": bda_uuid},
    )
    logger.debug(
        f"From BDA mapping table used {bda_uuid=} to retrieve {job_id=} {username=}"
    )

    # Read in BDA result, dump vtt and two txt files
    vtt_output_key = os.path.join(VTT_DESTINATION_PREFIX, username, job_id + ".vtt")
    txt_output_key = os.path.join(DESTINATION_PREFIX, username, job_id + ".txt")
    bda_txt_output_key = os.path.join(BDA_DESTINATION_PREFIX, username, job_id + ".txt")

    logger.debug(f"{vtt_output_key=} {txt_output_key=} {bda_txt_output_key=}")

    # Read BDA output from s3, convert to vtt
    try:
        # Download bda from s3
        bda_output = (
            s3.get_object(Bucket=S3_BUCKET, Key=bda_json_key)["Body"].read().decode()
        )
        # Convert to json
        bda_output_json = json.loads(bda_output)

        # Convert to vtt
        vtt_string = bda_output_to_vtt(bda_output_json)

        # Upload vtt to s3 as a text file
        put_response = s3.put_object(
            Body=bytes(vtt_string, "utf-8"), Bucket=S3_BUCKET, Key=vtt_output_key
        )
        logger.debug(f"Response to putting text into s3: {put_response}")

        # Save vtt URI to dynamodb
        response = invoke_lambda(
            lambda_client=lambda_client,
            lambda_function_name=DDB_LAMBDA_NAME,
            action="update_ddb_entry",
            params={
                "job_id": job_id,
                "username": username,
                "new_item_name": "vtt_transcript_uri",
                "new_item_value": os.path.join("s3://", S3_BUCKET, vtt_output_key),
            },
        )

        logger.debug(f"Response to putting vtt URI into {job_id}: {response}")

        # Also convert to txt of info extracted from images in the video
        # (this is an empty string if an audio file is supplied)
        bda_output_string = build_simplified_bda_video_string(bda_output_json)

        # Upload bda string to s3 as a text file
        if bda_output_string:
            put_response = s3.put_object(
                Body=bytes(bda_output_string, "utf-8"),
                Bucket=S3_BUCKET,
                Key=bda_txt_output_key,
            )
            logger.debug(f"Response to putting bda text into s3: {put_response}")
        else:
            logger.info(f"BDA output string was empty for {job_id=}")

        # Convert vtt transcript into human readable form for LLM
        transcript_processed = build_timestamped_segmented_transcript(vtt_string)

        # Build json with metadata for Bedrock KB to index and filter on later
        # Note: need to get media_uri from DDB
        media_name = invoke_lambda(
            lambda_client=lambda_client,
            lambda_function_name=DDB_LAMBDA_NAME,
            action="retrieve_media_name_by_jobid",
            params={
                "job_id": job_id,
                "username": username,
            },
        )

        meta_json = build_kb_metadata_json(username=username, media_name=media_name)

        # Save txt URI to dynamodb
        response = invoke_lambda(
            lambda_client=lambda_client,
            lambda_function_name=DDB_LAMBDA_NAME,
            action="update_ddb_entry",
            params={
                "job_id": job_id,
                "username": username,
                "new_item_name": "txt_transcript_uri",
                "new_item_value": os.path.join("s3://", S3_BUCKET, txt_output_key),
            },
        )

        logger.debug(f"Response to putting text uri into {job_id}: {response}")

        # Upload txt transcript to s3 as a text file
        put_response = s3.put_object(
            Body=bytes(transcript_processed, "utf-8"),
            Bucket=S3_BUCKET,
            Key=txt_output_key,
        )
        logger.debug(f"Response to putting text into s3: {put_response}")

        # Upload metadata to s3 as a json file
        # of form blahblah.txt.metadata.json (required by Bedrock KB)
        metadata_output_key = txt_output_key + ".metadata.json"
        put_response = s3.put_object(
            Body=bytes(json.dumps(meta_json, indent=2), "utf-8"),
            Bucket=S3_BUCKET,
            Key=metadata_output_key,
        )
        logger.debug(f"Response to putting text into s3: {put_response}")

    except Exception as e:
        logger.warning(f"ERROR Exception caught in postprocess-bda-lambda: {e}.")
        # Update job status in dynamodb
        response = invoke_lambda(
            lambda_client=lambda_client,
            lambda_function_name=DDB_LAMBDA_NAME,
            action="update_job_status",
            params={
                "job_id": job_id,
                "username": username,
                "new_status": JobStatus.FAILED.value,
            },
        )
        raise

    # Update job status in dynamodb
    response = invoke_lambda(
        lambda_client=lambda_client,
        lambda_function_name=DDB_LAMBDA_NAME,
        action="update_job_status",
        params={
            "job_id": job_id,
            "username": username,
            "new_status": JobStatus.BDA_PROCESSING_COMPLETE.value,
        },
    )

    return {
        "statusCode": 200,
        "body": json.dumps("postprocess-bda routine complete."),
    }
