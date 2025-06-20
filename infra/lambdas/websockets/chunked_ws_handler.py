# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import traceback
from datetime import datetime
from decimal import Decimal as decimal
from queue import SimpleQueue
from threading import Thread
from typing import BinaryIO, Literal, TypedDict

import boto3
import botocore
from boto3.dynamodb.conditions import Attr, Key

# Import existing KB utilities
from kb.kb_utils import KBQARAG

WEBSOCKET_SESSION_TABLE_NAME = os.environ["WEBSOCKET_SESSION_TABLE_NAME"]
KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
AWS_REGION = os.environ["AWS_REGION"]
NUM_CHUNKS = os.environ["NUM_CHUNKS"]
FOUNDATION_MODEL = os.environ["FOUNDATION_MODEL_ID"]
S3_BUCKET = os.environ.get("S3_BUCKET")
TEXT_TRANSCRIPTS_PREFIX = os.environ.get("TEXT_TRANSCRIPTS_PREFIX")
BDA_OUTPUT_PREFIX = os.environ.get("BDA_OUTPUT_PREFIX")

# Initialize clients
dynamodb_client = boto3.resource("dynamodb")
table = dynamodb_client.Table(WEBSOCKET_SESSION_TABLE_NAME)
cognito_client = boto3.client("cognito-idp")
s3_client = boto3.client("s3")

# Initialize KB QA RAG handler
kbqarag = KBQARAG(
    knowledge_base_id=KNOWLEDGE_BASE_ID,
    region_name=AWS_REGION,
    num_chunks=NUM_CHUNKS,
    foundation_model=FOUNDATION_MODEL,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class _NotifyCommand(TypedDict):
    type: Literal["notify"]
    payload: bytes | BinaryIO


class _FinishCommand(TypedDict):
    type: Literal["finish"]


_Command = _NotifyCommand | _FinishCommand


class NotificationSender:
    """Handles sending notifications to WebSocket clients"""
    
    def __init__(self, endpoint_url: str, connection_id: str) -> None:
        self.commands = SimpleQueue[_Command]()
        self.endpoint_url = endpoint_url
        self.connection_id = connection_id

    def run(self):
        """Run the notification sender in a separate thread"""
        gatewayapi = boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=self.endpoint_url,
        )

        while True:
            command = self.commands.get()
            if command["type"] == "notify":
                try:
                    gatewayapi.post_to_connection(
                        ConnectionId=self.connection_id,
                        Data=command["payload"],
                    )

                except (
                    gatewayapi.exceptions.GoneException,
                    gatewayapi.exceptions.ForbiddenException,
                ) as e:
                    logger.exception(
                        f"Shutdown the notification sender due to an exception: {e}"
                    )
                    break

                except Exception as e:
                    logger.exception(f"Failed to send notification: {e}")

            elif command["type"] == "finish":
                break

    def finish(self):
        """Signal the notification sender to finish"""
        self.commands.put({"type": "finish"})

    def notify(self, payload: bytes | BinaryIO):
        """Queue a notification to be sent"""
        self.commands.put({"type": "notify", "payload": payload})

    def send_streaming_response(self, generation_event: dict):
        """Send a streaming response event to the client"""
        data = json.dumps(generation_event).encode("utf-8")
        self.notify(payload=data)


def verify_token(token: str) -> dict:
    """Verify Cognito JWT token and return decoded payload"""
    try:
        response = cognito_client.get_user(AccessToken=token)
        return {
            "sub": response["Username"],
            "username": response["Username"]
        }
    except cognito_client.exceptions.NotAuthorizedException as e:
        logger.error(f"Token verification failed: {e}")
        raise Exception("Invalid or expired token")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise Exception("Token verification failed")


def process_chat_input(
    user_id: str,
    chat_input: dict,
    notificator: NotificationSender,
) -> dict:
    """Process chat input and stream responses to the client"""
    logger.info(f"Processing chat input for user {user_id}: {chat_input}")

    try:
        messages = json.loads(chat_input["messages"])
        username = chat_input.get("username", user_id)
        media_names = chat_input.get("media_names", [])
        if media_names:
            media_names = json.loads(media_names)
        transcript_job_id = chat_input.get("transcript_job_id", None)

        # Validate input
        if not (messages and username):
            raise ValueError("Missing required fields: messages and username")

        # If no specific media file is selected, use RAG over all files
        # If 2+ media files are selected, use RAG over just those files
        if len(media_names) == 0 or len(media_names) > 1:
            generation_stream = kbqarag.retrieve_and_generate_answer_stream(
                messages=messages,
                username=username,
                media_names=media_names,
            )
            for generation_event in generation_stream:
                notificator.send_streaming_response(generation_event)

        else:  # Single media file selected
            # Retrieve the full transcript from S3
            logger.info(
                f"Retrieving transcript: s3://{S3_BUCKET}/{TEXT_TRANSCRIPTS_PREFIX}/{username}/{transcript_job_id}.txt"
            )
            full_transcript_from_s3 = (
                s3_client.get_object(
                    Bucket=S3_BUCKET,
                    Key=f"{TEXT_TRANSCRIPTS_PREFIX}/{username}/{transcript_job_id}.txt",
                )["Body"]
                .read()
                .decode("utf-8")
            )
            
            # Check for BDA output (for video files)
            try:
                bda_output = (
                    s3_client.get_object(
                        Bucket=S3_BUCKET,
                        Key=f"{BDA_OUTPUT_PREFIX}/{username}/{transcript_job_id}.txt",
                    )["Body"]
                    .read()
                    .decode("utf-8")
                )
            except botocore.exceptions.ClientError:
                logger.info(f"No BDA output exists for {transcript_job_id}")
                bda_output = ""

            generation_stream = kbqarag.generate_answer_no_chunking_stream(
                messages=messages,
                media_name=media_names[0],
                full_transcript=full_transcript_from_s3,
                bda_output=bda_output,
            )
            for generation_event in generation_stream:
                notificator.send_streaming_response(generation_event)

        return {"statusCode": 200, "body": "Message sent."}

    except Exception as e:
        logger.exception(f"Failed to process chat input: {e}")
        error_response = {
            "status": "ERROR",
            "reason": f"Failed to process request: {str(e)}",
        }
        notificator.send_streaming_response(error_response)
        return {
            "statusCode": 500,
            "body": json.dumps(error_response),
        }


def handler(event, context):
    """Main WebSocket handler implementing chunked message protocol"""
    logger.info(f"Received event: {event}")
    route_key = event["requestContext"]["routeKey"]

    if route_key == "$connect":
        return {"statusCode": 200, "body": "Connected."}
    elif route_key == "$disconnect":
        return {"statusCode": 200, "body": "Disconnected."}

    connection_id = event["requestContext"]["connectionId"]
    domain_name = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    endpoint_url = f"https://{domain_name}/{stage}"
    
    notificator = NotificationSender(
        endpoint_url=endpoint_url,
        connection_id=connection_id,
    )

    now = datetime.now()
    expire = int(now.timestamp()) + 60 * 2  # 2 minutes from now
    body = json.loads(event["body"])
    step = body.get("step")
    token = body.get("token")

    notification_thread = Thread(
        target=lambda: notificator.run(),
        daemon=True,
    )
    notification_thread.start()

    try:
        # Handle chunked message protocol
        if step == "START":
            try:
                # Verify JWT token
                decoded = verify_token(token)
            except Exception as e:
                logger.exception(f"Invalid token: {e}")
                return {
                    "statusCode": 403,
                    "body": json.dumps({
                        "status": "ERROR",
                        "reason": "Invalid token.",
                    }),
                }

            user_id = decoded["sub"]

            # Store user id in DynamoDB
            table.put_item(
                Item={
                    "ConnectionId": connection_id,
                    "MessagePartId": decimal(0),  # Zero reserved for user ID
                    "UserId": user_id,
                    "expire": expire,
                }
            )
            return {"statusCode": 200, "body": "Session started."}

        elif step == "END":
            # Verify token again for END step
            try:
                decoded = verify_token(token)
                user_id = decoded["sub"]
            except Exception as e:
                logger.exception(f"Invalid token in END step: {e}")
                return {
                    "statusCode": 403,
                    "body": json.dumps({
                        "status": "ERROR",
                        "reason": "Invalid token.",
                    }),
                }

            # Retrieve user id from DynamoDB
            response = table.query(
                KeyConditionExpression=Key("ConnectionId").eq(connection_id),
                FilterExpression=Attr("UserId").exists(),
            )
            
            if not response["Items"]:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "status": "ERROR",
                        "reason": "Session not found.",
                    }),
                }

            stored_user_id = response["Items"][0]["UserId"]
            
            # Verify user ID matches
            if stored_user_id != user_id:
                return {
                    "statusCode": 403,
                    "body": json.dumps({
                        "status": "ERROR",
                        "reason": "User ID mismatch.",
                    }),
                }

            # Concatenate message parts
            message_parts = []
            last_evaluated_key = None

            while True:
                if last_evaluated_key:
                    response = table.query(
                        KeyConditionExpression=Key("ConnectionId").eq(connection_id)
                        & Key("MessagePartId").gte(1),  # Skip user ID record
                        ExclusiveStartKey=last_evaluated_key,
                    )
                else:
                    response = table.query(
                        KeyConditionExpression=Key("ConnectionId").eq(connection_id)
                        & Key("MessagePartId").gte(1),
                    )

                message_parts.extend(response["Items"])

                if "LastEvaluatedKey" in response:
                    last_evaluated_key = response["LastEvaluatedKey"]
                else:
                    break

            logger.info(f"Number of message chunks: {len(message_parts)}")
            message_parts.sort(key=lambda x: x["MessagePartId"])
            full_message = "".join(item["MessagePart"] for item in message_parts)

            # Process the concatenated full message
            try:
                chat_input = json.loads(full_message)
                return process_chat_input(
                    user_id=user_id,
                    chat_input=chat_input,
                    notificator=notificator,
                )
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse concatenated message: {e}")
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "status": "ERROR",
                        "reason": "Invalid message format.",
                    }),
                }

        else:
            # Handle BODY step - store message part
            part_index = body["index"] + 1  # Start from 1 (0 reserved for user ID)
            message_part = body["part"]

            # Store the message part with its index
            table.put_item(
                Item={
                    "ConnectionId": connection_id,
                    "MessagePartId": decimal(part_index),
                    "MessagePart": message_part,
                    "expire": expire,
                }
            )
            return {"statusCode": 200, "body": "Message part received."}

    except Exception as e:
        logger.exception(f"Operation failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "ERROR",
                "reason": str(e),
            }),
        }

    finally:
        notificator.finish()
        notification_thread.join(timeout=60)
