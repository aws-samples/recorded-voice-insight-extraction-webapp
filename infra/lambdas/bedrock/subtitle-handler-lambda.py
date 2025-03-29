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

"""Lambda to handle retrieving subtitles from s3 and optionally translating them"""

import json
import logging
import os
import re
import boto3


logger = logging.getLogger()
logger.setLevel("INFO")

S3_BUCKET = os.environ.get("S3_BUCKET")
TRANSCRIPTS_PREFIX = os.environ.get("TRANSCRIPTS_PREFIX")

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    """Retrieve transcript from s3 and return as vtt string (subtitles)
    Optionally translate a portion of the vtt to a different language"""
    # When this lambda is called by the frontend via API gateway, the event
    # has a 'body' key. When this lambda is called by other lambdas, this is
    # unnecessary

    logger.debug(f"{event=}")

    if "body" in event:
        event = json.loads(event["body"])

    username = event.get("username", None)
    transcript_job_id = event.get("transcript_job_id", None)
    translation_start_time = event.get("translation_start_time", None)
    translation_duration = event.get("translation_duration", None)
    translation_destination_language = event.get(
        "translation_destination_language", None
    )

    # Assert username and transcript_job_id are always supplied
    assert username and transcript_job_id, "Missing username and/or transcript_job_id"

    # Assert that if ANY of the translation arguments are supplied, they ALL are
    # Create a list of the translation-related variables and count how many are None
    none_count = [
        translation_start_time,
        translation_duration,
        translation_destination_language,
    ].count(None)
    assert none_count == 0 or none_count == 3, (
        "Translation parameters must be either all provided or all omitted"
    )
    if none_count == 0:
        raise NotImplementedError("Haven't implemented transcription translation yet.")

    # Retrieve the full_transcript from s3 via the job_id
    logger.info(
        f"Attempting to retrieve: s3://{S3_BUCKET}/{TRANSCRIPTS_PREFIX}/{username}/{transcript_job_id}.vtt"
    )
    try:
        full_transcript_vtt_string = (
            s3_client.get_object(
                Bucket=S3_BUCKET,
                Key=f"{TRANSCRIPTS_PREFIX}/{username}/{transcript_job_id}.vtt",
            )["Body"]
            .read()
            .decode("utf-8")
        )

    except Exception as e:
        return {"statusCode": 500, "body": f"Internal server error: {e}"}

    return {"statusCode": 200, "body": json.dumps(full_transcript_vtt_string)}
