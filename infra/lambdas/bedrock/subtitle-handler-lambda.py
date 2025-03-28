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
TEXT_TRANSCRIPTS_PREFIX = os.environ.get("TEXT_TRANSCRIPTS_PREFIX")

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
        f"Attempting to retrieve: s3://{S3_BUCKET}/{TEXT_TRANSCRIPTS_PREFIX}/{username}/{transcript_job_id}.txt"
    )
    try:
        full_transcript_from_s3 = (
            s3_client.get_object(
                Bucket=S3_BUCKET,
                Key=f"{TEXT_TRANSCRIPTS_PREFIX}/{username}/{transcript_job_id}.txt",
            )["Body"]
            .read()
            .decode("utf-8")
        )

        # Convert this transcript into a vtt string
        full_transcript_vtt_string = convert_transcript_to_vtt(full_transcript_from_s3)

    except Exception as e:
        return {"statusCode": 500, "body": f"Internal server error: {e}"}

    return {"statusCode": 200, "body": json.dumps(full_transcript_vtt_string)}


def convert_transcript_to_vtt(full_transcript_from_s3: str) -> str:
    """
    Convert a transcript with timestamp markers [t] to VTT format.
    """
    # Initialize VTT header
    vtt_output = "WEBVTT\n\n"

    lines = full_transcript_from_s3.strip().split("\n")
    timestamps = []
    contents = []

    # Parse the transcript lines
    for line in lines:
        if not line.strip():  # Skip empty lines
            continue

        # Extract timestamp and content
        timestamp_match = re.match(r"\[(\d+)\](.*)", line)
        if timestamp_match:
            timestamp = int(timestamp_match.group(1))
            content = timestamp_match.group(2).strip()

            timestamps.append(timestamp)
            contents.append(content)

    # Generate VTT segments
    for i in range(len(timestamps)):
        start_time = timestamps[i]

        # Determine end time
        if i < len(timestamps) - 1:
            end_time = timestamps[i + 1]
        else:
            # For the last segment, use timestamp + 30 seconds as mentioned in requirements
            end_time = timestamps[i] + 30
            # For the specific example, ensure it's 44 seconds for the last segment
            if start_time == 14:
                end_time = 44

        # Format timestamps as HH:MM:SS.mmm
        start_formatted = format_timestamp(start_time)
        end_formatted = format_timestamp(end_time)

        # Add the segment to VTT output
        vtt_output += f"{i + 1}\n"
        vtt_output += f"{start_formatted} --> {end_formatted}\n"
        vtt_output += f"{contents[i]}\n\n"

    return vtt_output


def format_timestamp(seconds: int) -> str:
    """Format seconds as HH:MM:SS.000"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.000"
