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

import datetime
import os
from typing import Any


def update_ddb_entry(
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


def update_job_status(table, uuid: str, username: str, new_status: str):
    """Update transcription job status
    "table" input is a dynamo DB resource Table"""
    assert new_status in [
        "Transcribing",
        "Indexing",
        "Transcription Complete",
        "Completed",
        "Failed",
        "In Transcription Queue",
    ]

    return update_ddb_entry(
        table=table,
        uuid=uuid,
        username=username,
        new_item_name="job_status",
        new_item_value=new_status,
    )


def create_ddb_entry(table, uuid: str, media_uri: str, username: str):
    """Create a new entry in dynamodb, with timestamp"""

    return table.put_item(
        Item={
            "UUID": uuid,
            "username": username,
            "media_uri": media_uri,
            "job_creation_time": str(datetime.datetime.now()),
            "media_name": os.path.split(media_uri)[-1],
            "job_status": "In Transcription Queue",
        }
    )


def retrieve_media_name_by_jobid(table, job_id: str, username: str) -> str | None:
    """Given jobid and username return media_name
    "table" input is a dynamo DB resource Table"""

    response = table.get_item(
        Key={"username": username, "UUID": job_id}, ProjectionExpression="media_name"
    )["Item"]
    return response["media_name"]


def batch_update_job_statuses(table, ingestion_job_id: str, new_status: str):
    """Scan through table and update status of all rows with ingestion_job_id to new_status"""
    response = table.scan(
        FilterExpression="ingestion_job_id = :job_id",
        ExpressionAttributeValues={":job_id": ingestion_job_id},
    )

    for item in response["Items"]:
        table.update_item(
            Key={"UUID": item["UUID"], "username": item["username"]},
            UpdateExpression="SET job_status = :status",
            ExpressionAttributeValues={":status": new_status},
        )
