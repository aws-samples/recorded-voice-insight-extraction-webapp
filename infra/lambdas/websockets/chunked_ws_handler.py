# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import traceback
from datetime import datetime
from decimal import Decimal as decimal

import boto3
import botocore
from boto3.dynamodb.conditions import Attr, Key

WEBSOCKET_SESSION_TABLE_NAME = os.environ["WEBSOCKET_SESSION_TABLE_NAME"]
ASYNC_STREAMING_LAMBDA_NAME = os.environ["ASYNC_STREAMING_LAMBDA_NAME"]

# Initialize clients
dynamodb_client = boto3.resource("dynamodb")
table = dynamodb_client.Table(WEBSOCKET_SESSION_TABLE_NAME)
cognito_client = boto3.client("cognito-idp")
lambda_client = boto3.client("lambda")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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

    now = datetime.now()
    expire = int(now.timestamp()) + 60 * 2  # 2 minutes from now
    body = json.loads(event["body"])
    step = body.get("step")
    token = body.get("token")

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

            # Parse the concatenated full message
            try:
                chat_input = json.loads(full_message)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse concatenated message: {e}")
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "status": "ERROR",
                        "reason": "Invalid message format.",
                    }),
                }

            # Start async streaming by invoking separate Lambda
            try:
                lambda_client.invoke(
                    FunctionName=ASYNC_STREAMING_LAMBDA_NAME,
                    InvocationType='Event',  # Async invocation
                    Payload=json.dumps({
                        'connection_id': connection_id,
                        'endpoint_url': endpoint_url,
                        'chat_input': chat_input,
                        'user_id': user_id
                    })
                )
                logger.info(f"Successfully invoked async streaming Lambda for connection {connection_id}")
            except Exception as e:
                logger.error(f"Failed to invoke async streaming Lambda: {e}")
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "status": "ERROR",
                        "reason": "Failed to start streaming process.",
                    }),
                }
            
            # Return immediately - streaming continues in separate Lambda
            return {"statusCode": 200, "body": "Streaming started"}

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
