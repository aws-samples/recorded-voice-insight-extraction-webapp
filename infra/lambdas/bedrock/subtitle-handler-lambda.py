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

import boto3
import botocore.exceptions
from .subtitle_utils import translate_vtt
from lambda_utils.cors_utils import CORSResponse

logger = logging.getLogger()
logger.setLevel("DEBUG")

S3_BUCKET = os.environ.get("S3_BUCKET")
TRANSCRIPTS_PREFIX = os.environ.get("TRANSCRIPTS_PREFIX")
FOUNDATION_MODEL_ID = os.environ.get("FOUNDATION_MODEL_ID")

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    """Retrieve transcript from s3 and return as vtt string (subtitles)
    Optionally translate a portion of the vtt to a different language"""
    # When this lambda is called by the frontend via API gateway, the event
    # has a 'body' key. When this lambda is called by other lambdas, this is
    # unnecessary

    logger.debug(f"{event=}")

    try:
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
        if not (username and transcript_job_id):
            return CORSResponse.error_response(
                f"Missing username and/or transcript_job_id. username={username} transcript_job_id={transcript_job_id}",
                400,
            )

        # Assert that if ANY of the translation arguments are supplied, they ALL are
        # Create a list of the translation-related variables and count how many are None
        none_count = [
            translation_start_time,
            translation_duration,
            translation_destination_language,
        ].count(None)

        if not (none_count == 0 or none_count == 3):
            return CORSResponse.error_response(
                f"Translation parameters must be either all provided or all omitted: translation_start_time={translation_start_time} translation_duration={translation_duration} translation_destination_language={translation_destination_language}",
                400,
            )

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
            return CORSResponse.error_response(
                f"Failed to retrieve transcript: {str(e)}", 500
            )

        # If no translation is needed, return vtt string directly
        if not translation_start_time:
            return CORSResponse.success_response(full_transcript_vtt_string)

        # If translation is needed, translate
        try:
            translated_vtt_string = translate_vtt(
                foundation_model_id=FOUNDATION_MODEL_ID,
                vtt_string=full_transcript_vtt_string,
                target_language=translation_destination_language,
                start_time_seconds=float(translation_start_time),
                end_time_seconds=float(translation_start_time)
                + float(translation_duration),
            )
        # If LLM performing translation is throttled, return 503.
        # The frontend should catch the 503 code and display a warning to the user.
        except botocore.exceptions.ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in [
                "ThrottlingException",
                "TooManyRequestsException",
                "RequestLimitExceeded",
            ]:
                return {
                    "statusCode": 503,
                    "headers": CORSResponse.get_cors_headers(),
                    "body": json.dumps({"message": f"Throttling error: {str(e)}"}),
                }
            else:
                # Re-raise if it's not a throttling error
                raise

        return CORSResponse.success_response(translated_vtt_string)

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return CORSResponse.error_response(f"Internal server error: {str(e)}", 500)
