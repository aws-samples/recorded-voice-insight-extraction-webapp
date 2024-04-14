import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel("INFO")

S3_BUCKET = os.environ.get("S3_BUCKET")
SOURCE_PREFIX = os.environ.get("SOURCE_PREFIX")
DESTINATION_PREFIX = os.environ.get("DESTINATION_PREFIX")
LLM_ID = os.environ.get("LLM_ID")
DYNAMO_TABLE_NAME = os.environ.get("DYNAMO_TABLE_NAME")

# Initialize the s3 client
s3 = boto3.client("s3")

# Initialize the dynamo db resource
dyn_resource = boto3.resource("dynamodb")
# TODO: make sure it exists or something?
dyn_table = dyn_resource.Table(name=DYNAMO_TABLE_NAME)

# Initialize the Amazon Bedrock runtime client
bedrock_client = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")


def update_ddb_entry(table, uuid, new_item_name, new_item_value):
    # Update an existing item in the dynamodb
    return table.update_item(
        Key={"UUID": uuid},
        UpdateExpression="SET #new_attr = :new_value",
        ExpressionAttributeNames={"#new_attr": new_item_name},
        ExpressionAttributeValues={":new_value": new_item_value},
    )


def lambda_handler(event, context):
    logger.info("generate-summary-lambda handler called.")
    logger.info(f"{event=}")
    logger.info(f"{context=}")

    # Read in txt filet
    txt_transcript_key = event["Records"][0]["s3"]["object"]["key"]
    logger.info(f"{txt_transcript_key=}")
    filename = os.path.split(txt_transcript_key)[1]
    uuid, extension = os.path.splitext(filename)

    # This should never fail, if s3 event notifications are set up correctly
    try:
        assert extension == ".txt"
    except AssertionError as err:
        logger.exception(
            f"Unable to read text from non-txt file: {txt_transcript_key}."
        )
        raise err

    output_key = os.path.join(DESTINATION_PREFIX, uuid + "-summary.txt")
    logger.info(f"{output_key=}")

    try:
        # Download txt_uri from s3 to tmp dir, read it in
        # TODO: read directly from s3 without needing tmp dirs...
        # same TODO for convert-json-to-txt-lambda
        tmp_txt_file = "/tmp/txt_transcript.txt"
        s3.download_file(S3_BUCKET, txt_transcript_key, tmp_txt_file)
        transcript = open(tmp_txt_file, "r").read()
        logger.info(f"{transcript=}")

        # Generate summary w/ bedrock
        summary = gen_summary_from_transcript(transcript)
        logger.info(f"{summary=}")
        # Dump text to tmp dir
        tmp_txt_file = "/tmp/transcript_summary.txt"
        with open(tmp_txt_file, "w") as f:
            f.write(summary)

        # Upload tmp_txt_file from tmp dir to s3 (output_uri)
        s3.upload_file(
            tmp_txt_file,
            S3_BUCKET,
            output_key,
        )

        # Save summary to dynamodb
        update_ddb_entry(dyn_table, uuid, "llm_summary", summary)

    except Exception as e:
        logger.error(f"ERROR Exception caught in generate-summary-lambda: {e}.")
        raise

    return {
        "statusCode": 200,
        "body": json.dumps("Summary generation routine complete."),
    }


def invoke_claude_3_with_text(prompt: str) -> dict:
    """
    Invokes Anthropic Claude 3 Sonnet to run an inference using the input
    provided in the request body.

    :param prompt: The prompt that you want Claude 3 to complete.
    :return: Inference response from the model.
    """

    try:
        logger.info("Calling bedrock!")
        response = bedrock_client.invoke_model(
            modelId=LLM_ID,
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 5000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": prompt}],
                        }
                    ],
                    "temperature": 1,
                    "top_p": 0.999,
                    "top_k": 250,
                }
            ),
        )
        logger.info(f"Bedrock response: {response}")

        # Process and print the response
        result = json.loads(response.get("body").read())
        input_tokens = result["usage"]["input_tokens"]
        output_tokens = result["usage"]["output_tokens"]
        output_list = result.get("content", [])

        logger.info("Invocation details:")
        logger.info(f"- The input length is {input_tokens} tokens.")
        logger.info(f"- The output length is {output_tokens} tokens.")

        logger.info(f"- The model returned {len(output_list)} response(s):")
        for output in output_list:
            logger.info(output["text"])

        return result

    except ClientError as err:
        logger.error(
            f"Couldn't invoke Bedrock model {LLM_ID}. Here's why: %s: %s",
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise


def gen_summary_from_transcript(transcript: str) -> str:
    FULL_PROMPT = (
        "I am a consultant building a generative AI application for a customer. "
        "We are in the early phases of the engagement, and have conducted a "
        "discovery workshop. The purpose of the workshop was to concretely "
        "determine the scope of the POC, responsibilities, success metrics, "
        "and next steps. I transcribed a recording of the workshop and will "
        "provide the transcript to you below. Please write me a one page summary "
        "of the meeting, emphasizing things like use case description, next steps, "
        "potential obstacles identified, success criteria, and timelines. Here is "
        "the meeting transcript:\n"
        "<transcript>\n"
        f"{transcript}\n"
        "</transcript>"
    )

    res = invoke_claude_3_with_text(FULL_PROMPT)
    output_list = res.get("content", [])
    assert len(output_list) == 1, f"Output list has len {len(output_list)}, expected 1."
    return output_list[0]["text"]
