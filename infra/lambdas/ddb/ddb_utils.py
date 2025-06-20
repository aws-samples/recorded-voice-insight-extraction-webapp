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


"""Utilities related to dynamodb. Functions without a leading underscore are
generally called by the frontend (via API Gateway), while functions with leading
underscore are used internally by the backend lambdas."""

import datetime
import os
from typing import Any

from boto3.dynamodb.conditions import Key, Attr
from schemas.job_status import JobStatus


def _update_ddb_entry(
    table, uuid: str, username: str, new_item_name: str, new_item_value: Any
):
    """Update an existing item in the dynamodb
    (also works to add a new field to an existing item)
    "table" input is a dynamo DB resource Table"""

    return table.update_item(
        Key={"username": username, "UUID": uuid},
        UpdateExpression="SET #new_attr = :new_value",
        ExpressionAttributeNames={"#new_attr": new_item_name},
        ExpressionAttributeValues={":new_value": new_item_value},
    )


def _update_job_status(table, uuid: str, username: str, new_status: JobStatus):
    """Update transcription job status
    "table" input is a dynamo DB resource Table"""

    return _update_ddb_entry(
        table=table,
        uuid=uuid,
        username=username,
        new_item_name="job_status",
        new_item_value=new_status.value,
    )


def _create_ddb_entry(table, uuid: str, media_uri: str, username: str):
    """Create a new entry in dynamodb, with timestamp"""

    return table.put_item(
        Item={
            "UUID": uuid,
            "username": username,
            "media_uri": media_uri,
            "job_creation_time": str(datetime.datetime.now()),
            "media_name": os.path.split(media_uri)[-1],
            "job_status": JobStatus.IN_TRANSCRIPTION_QUEUE.value,
        }
    )


def _retrieve_media_name_by_jobid(table, job_id: str, username: str) -> str | None:
    """Given jobid and username return media_name
    "table" input is a dynamo DB resource Table"""

    response = table.get_item(
        Key={"username": username, "UUID": job_id}, ProjectionExpression="media_name"
    )["Item"]
    return response["media_name"]


def _retrieve_jobid_by_media_name(table, media_name: str, username: str) -> str | None:
    """Given media_name and username, return the job_id (UUID)
    "table" input is a dynamo DB resource Table"""

    # Query items with the username as partition key and filter by media_name
    response = table.query(
        KeyConditionExpression=Key("username").eq(username),
        FilterExpression=Attr("media_name").eq(media_name),
    )

    # Check if any items were returned
    if response["Count"] > 0:
        # Return the first matching UUID
        return response["Items"][0]["UUID"]
    else:
        return None


def retrieve_all_items(table, username) -> dict:
    """Query dynamodb table for rows from this username and return
    specific columns w/ optional max # of rows"""

    query_results = table.query(KeyConditionExpression=Key("username").eq(username))[
        "Items"
    ]

    return query_results


def _delete_job_by_id(table, username: str, job_id: str):
    """
    Delete a specific job entry from the DynamoDB table.

    Args:
        table: DynamoDB resource Table
        username: The username associated with the job
        job_id: The UUID of the job to delete

    Returns:
        The response from DynamoDB delete operation
    """
    response = table.delete_item(Key={"username": username, "UUID": job_id})

    return response


def _create_bda_map_entry(table, job_id: str, bda_uuid: str, username: str):
    """Create a new entry in BDA-uuid : App-uuid table"""

    return table.put_item(
        Item={"UUID": job_id, "BDA-UUID": bda_uuid, "username": username}
    )


def _retrieve_jobid_and_username_by_bda_uuid(table, bda_uuid: str):
    """Retrieve ReVIEW app job id from BDA assigned job id"""

    # Query items with the username as partition key and filter by media_name
    response = table.query(KeyConditionExpression=Key("BDA-UUID").eq(bda_uuid))

    # Check if any items were returned
    if response["Count"] > 0:
        # Return the first matching UUID along with username
        return response["Items"][0]["UUID"], response["Items"][0]["username"]
    else:
        return None
