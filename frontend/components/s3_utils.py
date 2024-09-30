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

"""Utilities related to accessing s3"""

import json
import os
import boto3

# Must match what's in the backend stack definition
BUCKET_NAME = os.environ["s3_bucket_name"]

# Initialize the s3 client
s3 = boto3.client("s3")


def retrieve_transcript_by_jobid(job_id: str, username: str) -> str:
    """Read transcript txt from s3 and return"""
    return (
        s3.get_object(
            Bucket=BUCKET_NAME, Key=f"transcripts-txt/{username}/{job_id}.txt"
        )["Body"]
        .read()
        .decode("utf-8")
    )


def retrieve_transcript_json_by_jobid(job_id: str, username: str) -> dict:
    """Read transcript json from s3 and return"""
    return json.load(
        s3.get_object(Bucket=BUCKET_NAME, Key=f"transcripts/{username}/{job_id}.json")[
            "Body"
        ]
    )


def retrieve_media_bytes(media_name: str, username: str) -> bytes:
    """Read media from s3 and return"""
    return s3.get_object(Bucket=BUCKET_NAME, Key=f"recordings/{username}/{media_name}")[
        "Body"
    ].read()


def uploadToS3(fileobj, username):
    try:
        s3.upload_fileobj(
            fileobj,
            BUCKET_NAME,
            os.path.join("recordings", username, os.path.split(fileobj.name)[-1]),
        )
        return True
    except FileNotFoundError:
        return False
