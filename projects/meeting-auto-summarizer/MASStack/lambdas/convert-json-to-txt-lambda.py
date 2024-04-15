import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel("INFO")

S3_BUCKET = os.environ.get("S3_BUCKET")
SOURCE_PREFIX = os.environ.get("SOURCE_PREFIX")
DESTINATION_PREFIX = os.environ.get("DESTINATION_PREFIX")
DYNAMO_TABLE_NAME = os.environ.get("DYNAMO_TABLE_NAME")

s3 = boto3.client("s3")
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
    """Convert json to txt, and also log both to dynamodb"""
    logger.debug("convert-json-to-txt-lambda handler called.")
    logger.debug(f"{event=}")
    logger.debug(f"{context=}")

    # Read in json file, dump to txt
    json_transcript_key = event["Records"][0]["s3"]["object"]["key"]
    logger.debug(f"{json_transcript_key=}")
    filename = os.path.split(json_transcript_key)[1]
    uuid, extension = os.path.splitext(filename)
    try:
        assert extension == ".json"
    except AssertionError as err:
        logger.exception(
            f"Unable to dump txt from non-json file: {json_transcript_key}."
        )
        raise err

    output_key = os.path.join(DESTINATION_PREFIX, uuid + ".txt")
    logger.debug(f"{output_key=}")

    try:
        # Download json_uri from s3 to tmp dir, read it in
        tmp_json_file = "/tmp/json_transcript.json"
        s3.download_file(S3_BUCKET, json_transcript_key, tmp_json_file)
        full_json = json.load(open(tmp_json_file, "r"))
        transcripts = full_json["results"]["transcripts"]
        assert len(transcripts) == 1

        # Save json to dynamodb
        response = update_ddb_entry(
            dyn_table, uuid, "json_transcript", json.dumps(full_json)
        )
        logger.debug(f"Response to putting json into {uuid}: {response}")

        transcript = transcripts[0]["transcript"]

        # Save txt to dynamodb
        response = update_ddb_entry(dyn_table, uuid, "txt_transcript", transcript)
        logger.debug(f"Response to putting text into {uuid}: {response}")

        # Dump text to tmp dir
        tmp_txt_file = "/tmp/txt_transcript.txt"
        with open(tmp_txt_file, "w") as f:
            f.write(transcript)

        # Upload tmp_txt_file from tmp dir to s3 (output_uri)
        s3.upload_file(
            tmp_txt_file,
            S3_BUCKET,
            output_key,
        )

    except AssertionError:
        logger.error(f"{len(transcripts)} transcripts found in results. Expected 1.")
    except Exception as e:
        logger.error(f"ERROR Exception caught in convert-json-to-txt-lambda: {e}.")
        raise

    return {
        "statusCode": 200,
        "body": json.dumps("json-to-text routine complete."),
    }
