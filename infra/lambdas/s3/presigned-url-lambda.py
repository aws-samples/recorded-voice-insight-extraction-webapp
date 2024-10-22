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
logger.setLevel("DEBUG")

S3_BUCKET = os.environ.get("S3_BUCKET")
RECORDINGS_PREFIX = os.environ.get("RECORDINGS_PREFIX")
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
        try:
            response = s3_client.generate_presigned_post(
                Bucket=S3_BUCKET,
                Key=f"{RECORDINGS_PREFIX}/{username}/{media_file_name}",
                ExpiresIn=PRESIGNED_URL_EXPIRATION_SECONDS,
            )
        except ClientError as e:
            logging.error(e)
            return None
    elif action == "download_media_file":  # GET
        username = event["username"]
        media_file_name = event["media_file_name"]
        try:
            response = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": S3_BUCKET,
                    "Key": f"{RECORDINGS_PREFIX}/{username}/{media_file_name}",
                },
                ExpiresIn=PRESIGNED_URL_EXPIRATION_SECONDS,
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
