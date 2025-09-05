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

import json
import logging
import os
import uuid
from urllib.parse import unquote_plus

import boto3

from schemas.job_status import JobStatus
from preprocessing.preprocessing_utils import (
    extract_username_from_s3_URI,
    get_bda_project_arn_by_project_name,
    BDA_PROJECT_NAME,
    BDA_OUTPUT_CONFIG,
)
from lambda_utils.invoke_lambda import invoke_lambda

logger = logging.getLogger()
logger.setLevel("INFO")

S3_BUCKET = os.environ.get("S3_BUCKET")
DESTINATION_PREFIX = os.environ.get("DESTINATION_PREFIX")
DDB_LAMBDA_NAME = os.environ.get("DDB_LAMBDA_NAME")
REGION = os.environ["AWS_REGION"]


# Create necessary BDA clients
bda_client = boto3.client("bedrock-data-automation")
bda_runtime_client = boto3.client("bedrock-data-automation-runtime")
s3_client = boto3.client("s3")

# Create a Lambda client so this lambda can invoke other lambdas
lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    logger.debug("generate-bda-lambda handler called.")
    logger.debug(f"{event=}")
    logger.debug(f"{context=}")

    logger.debug(
        f"recording_key from event: {event['Records'][0]['s3']['object']['key']}"
    )
    recording_key = unquote_plus(event["Records"][0]["s3"]["object"]["key"])

    logger.debug(f"decoded recording_key = {recording_key}")
    _path, filename = os.path.split(recording_key)
    _filename_without_extension, extension = os.path.splitext(filename)
    account_id = context.invoked_function_arn.split(":")[4]

    # Generate a random uuid for the job, which will be used
    # to track this bda through downstream tasks
    # (as the partition key in dynamodb)
    job_name = str(uuid.uuid4())
    logger.debug(f"{job_name=}")

    media_uri = f"s3://{S3_BUCKET}/{recording_key}"
    username = extract_username_from_s3_URI(media_uri)
    logger.debug(f"{media_uri=}")

    # Copy file to UUID-based name for BDA (BDA has strict filename requirements)
    # Use a different prefix to avoid triggering this lambda again
    uuid_filename = f"{job_name}{extension}"
    # Copy to bda-processing prefix instead of bda-recordings to avoid event loop
    uuid_key = f"bda-processing/{username}/{uuid_filename}"
    uuid_media_uri = f"s3://{S3_BUCKET}/{uuid_key}"
    
    logger.debug(f"Copying from {recording_key} to {uuid_key}")
    
    try:
        s3_client.copy_object(
            Bucket=S3_BUCKET,
            CopySource={'Bucket': S3_BUCKET, 'Key': recording_key},
            Key=uuid_key
        )
        logger.info(f"Copied {recording_key} to {uuid_key} for BDA processing")
    except Exception as e:
        logger.error(f"Failed to copy file for BDA: {e}")
        raise
    # Use job name (no spaces, etc) as the output file name, because output
    # has similar regex requirements

    # Create item in dynamodb to track media_uri (use original media_uri for display)
    response = invoke_lambda(
        lambda_client=lambda_client,
        lambda_function_name=DDB_LAMBDA_NAME,
        action="create_ddb_entry",
        params={"job_id": job_name, "media_uri": media_uri, "username": username},
    )
    logger.debug(f"Response to creating dynamodb item {job_name}: {response}")

    # Create BDA project if it doesn't exist
    # (this should only happen once ever)
    try:
        response = bda_client.create_data_automation_project(
            projectName=BDA_PROJECT_NAME,
            projectDescription="ReVIEW Application BDA Project",
            projectStage="LIVE",
            standardOutputConfiguration=BDA_OUTPUT_CONFIG,
        )
        project_arn = response["projectArn"]
    except bda_client.exceptions.ConflictException:
        logger.info(f"Project {BDA_PROJECT_NAME} already exists, not recreating.")
        project_arn = get_bda_project_arn_by_project_name(
            bda_client=bda_client, bda_project_name=BDA_PROJECT_NAME
        )
    logger.debug(f"BDA Project arn = {project_arn}")

    # Launch a BDA job
    try:
        bda_async_kwargs = {
            "inputConfiguration": {"s3Uri": uuid_media_uri},  # Use UUID-based URI for BDA
            "outputConfiguration": {
                "s3Uri": os.path.join("s3://", S3_BUCKET, DESTINATION_PREFIX)
            },
            "dataAutomationConfiguration": {
                "dataAutomationProjectArn": project_arn,
                "stage": "LIVE",
            },
            "dataAutomationProfileArn": f"arn:aws:bedrock:{REGION}:{account_id}:data-automation-profile/us.data-automation-v1",
        }
        logger.debug(f"Launching invoke_data_automation_async with {bda_async_kwargs=}")
        response = bda_runtime_client.invoke_data_automation_async(**bda_async_kwargs)
        logger.debug(f"BDA async response = {response}")
        bda_invocation_arn = response["invocationArn"]
        # BDA-assigned UUID is the end of the arn
        bda_uuid = bda_invocation_arn.split("/")[-1]
        logger.info(f"Started BDA job with invocation id {bda_uuid}")

    except Exception as e:
        logger.warning("ERROR Couldn't start BDA job.")
        logger.warning(f"Exception: {e}")
        raise

    # Associate BDA ID with our own job id in DDB
    # (separate mapping table)
    # Create item in dynamodb to track media_uri
    response = invoke_lambda(
        lambda_client=lambda_client,
        lambda_function_name=DDB_LAMBDA_NAME,
        action="store_bda_mapping",
        params={"job_id": job_name, "bda_uuid": bda_uuid, "username": username},
    )
    logger.debug(f"Stored BDA mapping into DDB: {job_name=} {bda_uuid=} {response=}")

    # Update job status in dynamodb
    response = invoke_lambda(
        lambda_client=lambda_client,
        lambda_function_name=DDB_LAMBDA_NAME,
        action="update_job_status",
        params={
            "job_id": job_name,
            "username": username,
            "new_status": JobStatus.BDA_PROCESSING.value,
        },
    )

    return {
        "statusCode": 200,
        "body": json.dumps(f"Started BDA job {job_name}"),
    }
