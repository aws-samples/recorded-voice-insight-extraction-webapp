"""Utilities related to accessing s3"""

import json
import os
import boto3

# Must match what's in the backend stack definition
BUCKET_NAME = os.environ["s3BucketName"]

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
