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
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel("INFO")

S3_BUCKET = os.environ.get("S3_BUCKET")
RECORDINGS_PREFIX = os.environ.get("RECORDINGS_PREFIX")
BDA_RECORDINGS_PREFIX = os.environ.get("BDA_RECORDINGS_PREFIX")
TEXT_TRANSCRIPTS_PREFIX = os.environ.get("TEXT_TRANSCRIPTS_PREFIX")
PRESIGNED_URL_EXPIRATION_SECONDS = int(1800)

# Create s3 client to generate presigned urls (s3v4 signing b/c this s3 bucket is encrypted)
config = Config(signature_version="s3v4")
s3_client = boto3.client("s3", config=config)


def lambda_handler(event, context):
    """Generate presigned urls for upload/download workflows"""

    logger.debug("presigned-url-lambda handler called.")
    logger.debug(f"{event=}")

    if "body" in event:
        event = json.loads(event["body"])

    action = event["action"]

    if action == "upload_media_file":  # POST
        username = event["username"]
        media_file_name = event["media_file_name"]
        use_bda = event["use_bda"] == "True"
        try:
            key = (
                f"{RECORDINGS_PREFIX}/{username}/{media_file_name}"
                if not use_bda
                else f"{BDA_RECORDINGS_PREFIX}/{username}/{media_file_name}"
            )
            response = s3_client.generate_presigned_post(
                Bucket=S3_BUCKET,
                Key=key,
                ExpiresIn=PRESIGNED_URL_EXPIRATION_SECONDS,
            )
        except ClientError as e:
            logging.error(e)
            return None
    elif action == "download_media_file":  # GET
        username = event["username"]
        media_file_name = event["media_file_name"]
        try:
            # Check both normal recordings prefix, and BDA recordings prefix
            # and return presigned url to whichever exists
            possible_keys = (
                f"{RECORDINGS_PREFIX}/{username}/{media_file_name}",
                f"{BDA_RECORDINGS_PREFIX}/{username}/{media_file_name}",
            )
            for key in possible_keys:
                if check_if_file_exists(bucket=S3_BUCKET, key=key):
                    return s3_client.generate_presigned_url(
                        "get_object",
                        Params={
                            "Bucket": S3_BUCKET,
                            "Key": key,
                        },
                        ExpiresIn=PRESIGNED_URL_EXPIRATION_SECONDS,
                    )
            raise boto3.exceptions.ClientError(
                f"Requested download of file {media_file_name} that DNE."
            )
        except ClientError as e:
            logging.error(e)
            return None
    elif action == "download_transcript_txt_file":  # GET
        username = event["username"]
        job_id = event["job_id"]
        try:
            response = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": S3_BUCKET,
                    "Key": f"{TEXT_TRANSCRIPTS_PREFIX}/{username}/{job_id}.txt",
                },
                ExpiresIn=PRESIGNED_URL_EXPIRATION_SECONDS,
            )
        except ClientError as e:
            logging.error(e)
            return None

    else:
        return {"statusCode": 400, "body": json.dumps("Invalid action")}

    return {
        "statusCode": 200,
        "body": json.dumps(response),
    }


def check_if_file_exists(bucket_name, key):
    """
    Check if a file exists in an S3 bucket

    Parameters:
    bucket_name (str): Name of the S3 bucket
    key (str): Key (path/filename) of the file in the bucket

    Returns:
    bool: True if file exists, False otherwise
    """
    s3_client = boto3.client("s3")

    try:
        # Use head_object to check if the object exists
        s3_client.head_object(Bucket=bucket_name, Key=key)
        return True
    except ClientError as e:
        # If the object doesn't exist, S3 will return a 404 error
        if e.response["Error"]["Code"] == "404":
            return False
        else:
            # If it's a different error (permissions, etc.), re-raise it
            raise
