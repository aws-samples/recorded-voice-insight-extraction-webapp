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

import boto3


def update_ddb_entry(
    table_name: str, uuid: str, username: str, new_item_name: str, new_item_value: Any
):
    """Update an existing item in the dynamodb
    (also works to add a new field to an existing item)"""

    dyn_resource = boto3.resource("dynamodb")
    # TODO: make sure it exists or something?
    table = dyn_resource.Table(name=table_name)

    return table.update_item(
        Key={"username": username, "UUID": uuid},
        UpdateExpression="SET #new_attr = :new_value",
        ExpressionAttributeNames={"#new_attr": new_item_name},
        ExpressionAttributeValues={":new_value": new_item_value},
    )


def update_job_status(table_name: str, uuid: str, username: str, new_status: str):
    """Update transcription job status"""
    assert new_status in ["In Progress", "Completed", "Failed", "In Queue"]

    return update_ddb_entry(
        table_name=table_name,
        uuid=uuid,
        username=username,
        new_item_name="transcription_status",
        new_item_value=new_status,
    )


def create_ddb_entry(table_name: str, uuid: str, media_uri: str, username: str):
    """Create a new entry in dynamodb, with timestamp"""

    dyn_resource = boto3.resource("dynamodb")
    # TODO: make sure it exists or something?
    table = dyn_resource.Table(name=table_name)

    return table.put_item(
        Item={
            "UUID": uuid,
            "username": username,
            "media_uri": media_uri,
            "job_creation_time": str(datetime.datetime.now()),
            "media_name": os.path.split(media_uri)[-1],
            "transcription_status": "In Queue",
        }
    )


def extract_username_from_s3_URI(uri: str) -> str:
    """URIs are like s3://bucket/blah/username/file_they_uploaded.mp4
    Return username
    TODO: test for security flaws, e.g. if usernames can contain / character"""
    return os.path.split(uri)[0].split("/")[-1]
