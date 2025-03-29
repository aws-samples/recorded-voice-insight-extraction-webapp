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


import os
import re


def extract_username_from_s3_URI(uri: str) -> str:
    """URIs are like s3://bucket/blah/username/file_they_uploaded.mp4
    Return username
    TODO: test for security flaws, e.g. if usernames can contain / character"""
    return os.path.split(uri)[0].split("/")[-1]


def extract_uuid_from_s3_URI(uri: str) -> str:
    """URIs are like s3://bucket/blah/username/[uuid].txt.metadata.json
    Return uuid"""
    return os.path.split(uri)[-1].split(".")[0]


# def build_timestamped_segmented_transcript(full_transcript_json: dict) -> str:
#     """Convert json transcript from Amazon Transcribe into a string that
#     is segmented into ([integer]) timestamps

#     [1] Hello.\n
#     [3] Thanks, for having me.\n
#     [10] This is a transcript!\n
#     """

#     items = full_transcript_json["results"]["items"]
#     lines = []  # list of strings
#     start_new_line = True
#     for item in items:
#         word = item["alternatives"][0]["content"]

#         if start_new_line:
#             lines.append("")
#             start_new_line = False
#             st = item["start_time"]
#             lines[-1] = f"[{int(float(st))}] {word}"
#         else:
#             if word == ".":
#                 lines[-1] += f"{word}"
#                 start_new_line = True
#             elif item["type"] == "punctuation":
#                 lines[-1] += f"{word}"
#             else:
#                 lines[-1] += f" {word}"
#     return "\n".join(lines)


def build_timestamped_segmented_transcript(vtt_string: str) -> str:
    """Convert vtt from Amazon Transcribe into a string that
    has integer timestamps easy for the LLM to comprehend

    [1] Hello.\n
    [3] Thanks, for having me.\n
    [10] This is a transcript!\n
    """

    # Split the input into lines
    lines = vtt_string.strip().split("\n")

    result_lines = []
    current_timestamp = None

    i = 0
    # Skip the "WEBVTT" header
    while i < len(lines) and lines[i] != "WEBVTT":
        i += 1
    if i < len(lines):
        i += 1  # Skip past "WEBVTT" line

    # Process the VTT content
    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Skip counter lines (just digits)
        if line.isdigit():
            i += 1
            continue

        # Check for timestamp lines
        timestamp_match = re.search(r"(\d+):(\d+):(\d+)\.\d+ -->", line)
        if timestamp_match:
            # Extract hours, minutes, seconds from the timestamp
            hours = int(timestamp_match.group(1))
            minutes = int(timestamp_match.group(2))
            seconds = int(timestamp_match.group(3))

            # Calculate total seconds
            current_timestamp = hours * 3600 + minutes * 60 + seconds
            i += 1
        elif current_timestamp is not None:
            # This is a subtitle text line
            result_lines.append(f"[{current_timestamp}] {line}")
            i += 1
        else:
            # Skip any other lines before we have a timestamp
            i += 1

    return "\n".join(result_lines)


def build_kb_metadata_json(username: str, media_name: str) -> dict:
    """Custom metadata for bedrock knowledge base to grab and include in OpenSearch for filtering"""
    return {"metadataAttributes": {"username": username, "media_name": media_name}}
