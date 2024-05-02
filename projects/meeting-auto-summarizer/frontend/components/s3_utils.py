"""Utilities related to accessing s3"""

import boto3

BUCKET_NAME = "meeting-auto-summarizer-assets"
# Initialize the s3 client
s3 = boto3.client("s3")


def retrieve_transcript_by_jobid(job_id: str) -> str:
    """Read transcript from s3 and return"""
    return (
        s3.get_object(Bucket=BUCKET_NAME, Key=f"transcripts-txt/{job_id}.txt")["Body"]
        .read()
        .decode("utf-8")
    )
