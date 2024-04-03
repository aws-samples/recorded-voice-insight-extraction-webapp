import json
import os
import re
import time

import boto3

S3_BUCKET = os.environ.get("S3_BUCKET")
SOURCE_PREFIX = os.environ.get("SOURCE_PREFIX")
DESTINATION_PREFIX = os.environ.get("DESTINATION_PREFIX")

transcribe_client = boto3.client("transcribe")


def lambda_handler(event, context):
    # Transcribe meeting recording to text
    recording_name = event["Records"][0]["s3"]["object"]["key"]
    job_tokens = recording_name.split("/")[1].split(".")
    media_format = job_tokens[1]
    # Ensure files have reasonable names, otherwise Transcribe will error
    pattern = r"[^0-9a-zA-Z._-]"
    cleaned = re.sub(pattern, "", job_tokens[0])
    job_name = "{}_{}".format(cleaned, int(time.time()))

    media_uri = "s3://{}/{}".format(S3_BUCKET, recording_name)
    output_key = "{}/{}.json".format(DESTINATION_PREFIX, job_name)

    try:
        job_args = {
            "TranscriptionJobName": job_name,
            "Media": {"MediaFileUri": media_uri},
            "MediaFormat": media_format,
            "IdentifyLanguage": True,
            "OutputBucketName": S3_BUCKET,
            "OutputKey": output_key,
        }

        response = transcribe_client.start_transcription_job(**job_args)
        _job = response["TranscriptionJob"]
        print("Started transcription job {}.".format(job_name))
    except Exception:
        print("Couldn't start transcription job %s.".format())
        raise

    return {
        "statusCode": 200,
        "body": json.dumps("Started transcription job {}".format(job_name)),
    }
