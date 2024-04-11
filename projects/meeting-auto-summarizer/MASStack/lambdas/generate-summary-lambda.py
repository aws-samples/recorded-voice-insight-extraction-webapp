### TODO: IMPLEMENT THIS WITH BEDROCK CALLING


# import json
# import logging
# import os

# import boto3

# logger = logging.getLogger()
# logger.setLevel("INFO")

# S3_BUCKET = os.environ.get("S3_BUCKET")
# SOURCE_PREFIX = os.environ.get("SOURCE_PREFIX")
# DESTINATION_PREFIX = os.environ.get("DESTINATION_PREFIX")

# s3 = boto3.client("s3")


# def lambda_handler(event, context):
#     logger.debug("convert-json-to-txt-lambda handler called.")
#     logger.debug(f"{event=}")
#     logger.debug(f"{context=}")

#     # Read in json file, dump to txt
#     json_transcript_key = event["Records"][0]["s3"]["object"]["key"]
#     logger.debug(f"{json_transcript_key=}")
#     filename = os.path.split(json_transcript_key)[1]
#     filename_without_extension, extension = os.path.splitext(filename)
#     try:
#         assert extension == ".json"
#     except AssertionError as err:
#         logger.exception(
#             f"Unable to dump txt from non-json file: {json_transcript_key}."
#         )
#         raise err

#     output_key = os.path.join(DESTINATION_PREFIX, filename_without_extension + ".txt")
#     logger.debug(f"{output_key=}")

#     try:
#         # Download json_uri from s3 to tmp dir, read it in
#         tmp_json_file = "/tmp/json_transcript.json"
#         s3.download_file(S3_BUCKET, json_transcript_key, tmp_json_file)
#         transcripts = json.load(open(tmp_json_file, "r"))["results"]["transcripts"]
#         assert len(transcripts) == 1

#         transcript = transcripts[0]["transcript"]
#         # Dump text to tmp dir
#         tmp_txt_file = "/tmp/txt_transcript.txt"
#         with open(tmp_txt_file, "w") as f:
#             f.write(transcript)

#         # Upload tmp_txt_file from tmp dir to s3 (output_uri)
#         s3.upload_file(
#             tmp_txt_file,
#             S3_BUCKET,
#             output_key,
#         )
#     except AssertionError:
#         logger.error(f"{len(transcripts)} transcripts found in results. Expected 1.")
#     except Exception as e:
#         logger.error(f"ERROR Exception caught in convert-json-to-txt-lambda: {e}.")
#         raise

#     return {
#         "statusCode": 200,
#         "body": json.dumps("json-to-text routine complete."),
#     }


def lambda_handler(event, context):
    print("Hello world")
    return {"statusCode": 200, "body": "Worked"}
