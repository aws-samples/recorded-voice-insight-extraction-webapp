import datetime
import json
import logging
import os
import uuid
from urllib.parse import unquote_plus

import boto3

logger = logging.getLogger()
logger.setLevel("INFO")

S3_BUCKET = os.environ.get("S3_BUCKET")
SOURCE_PREFIX = os.environ.get("SOURCE_PREFIX")
DESTINATION_PREFIX = os.environ.get("DESTINATION_PREFIX")
DYNAMO_TABLE_NAME = os.environ.get("DYNAMO_TABLE_NAME")

transcribe_client = boto3.client("transcribe")
dyn_resource = boto3.resource("dynamodb")
# TODO: make sure it exists or something?
dyn_table = dyn_resource.Table(name=DYNAMO_TABLE_NAME)


def update_ddb_entry(table, uuid, new_item_name, new_item_value):
    # Update an existing item in the dynamodb
    return table.update_item(
        Key={"UUID": uuid},
        UpdateExpression="SET #new_attr = :new_value",
        ExpressionAttributeNames={"#new_attr": new_item_name},
        ExpressionAttributeValues={":new_value": new_item_value},
    )


def lambda_handler(event, context):
    logger.debug("generate-transcript-lambda handler called.")
    logger.debug(f"{event=}")
    logger.debug(f"{context=}")

    # Transcribe meeting recording to text
    # Sometimes recording_key is url-encoded, and transcription API wants non-url-encoded
    # https://stackoverflow.com/questions/44779042/aws-how-to-fix-s3-event-replacing-space-with-sign-in-object-key-names-in-js
    logger.debug(
        f"recording_key from event: {event["Records"][0]["s3"]["object"]["key"]}"
    )
    recording_key = unquote_plus(event["Records"][0]["s3"]["object"]["key"])

    logger.debug(f"decoded recording_key = {recording_key}")
    _path, filename = os.path.split(recording_key)
    filename_without_extension, extension = os.path.splitext(filename)
    media_format = extension[1:]  # Drop the leading "." in extension
    assert media_format in [
        "mp3",
        "mp4",
        "wav",
        "flac",
        "ogg",
        "amr",
        "webm",
    ], f"Unacceptable media format for transcription: {media_format}"

    # Generate a random uuid for the job, which will be used
    # to track this transcript through downstream tasks
    # (as the partition key in dynamodb)
    # pattern = r"[^0-9a-zA-Z._-]"
    # cleaned = re.sub(pattern, "", filename_without_extension)
    # job_name = "{}_{}".format(cleaned, int(time.time()))
    job_name = str(uuid.uuid4())
    logger.debug(f"{job_name=}")

    media_uri = f"s3://{S3_BUCKET}/{recording_key}"
    logger.debug(f"{media_uri=}")
    # Use job name (no spaces, etc) as the output file name, because output
    # has similar regex requirements
    output_key = "{}/{}.json".format(DESTINATION_PREFIX, job_name)
    logger.debug(f"{output_key=}")
    job_args = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": media_uri},
        "MediaFormat": media_format,
        "IdentifyLanguage": True,
        "OutputBucketName": S3_BUCKET,
        "OutputKey": output_key,
    }
    logger.debug(f"{job_args=}")
    try:
        response = transcribe_client.start_transcription_job(**job_args)
        _job = response["TranscriptionJob"]
        logger.info(f"Started transcription job name {job_name}, id {_job}")

    except Exception as e:
        logger.error(f"ERROR Couldn't start transcription job {job_name}.")
        logger.error(f"Exception: {e}")
        raise

    # Create item in dynamodb to track media_uri
    response = dyn_table.put_item(
        Item={
            "UUID": job_name,
            "media_uri": media_uri,
            "job_creation_time": str(datetime.datetime.now()),
        }
    )
    logger.debug(f"Response to creating dynamodb item {uuid}: {response}")

    return {
        "statusCode": 200,
        "body": json.dumps(f"Started transcription job {job_name}"),
    }
