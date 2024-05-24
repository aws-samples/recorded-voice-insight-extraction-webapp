import datetime
import os
from typing import Any

import boto3


def update_ddb_entry(
    table_name: str, uuid: str, new_item_name: str, new_item_value: Any
):
    """Update an existing item in the dynamodb
    (also works to add a new field to an existing item)"""

    dyn_resource = boto3.resource("dynamodb")
    # TODO: make sure it exists or something?
    table = dyn_resource.Table(name=table_name)

    return table.update_item(
        Key={"UUID": uuid},
        UpdateExpression="SET #new_attr = :new_value",
        ExpressionAttributeNames={"#new_attr": new_item_name},
        ExpressionAttributeValues={":new_value": new_item_value},
    )


def update_job_status(table_name: str, uuid: str, new_status: str):
    """Update transcription job status"""
    assert new_status in ["In Progress", "Completed", "Failed"]

    return update_ddb_entry(
        table_name=table_name,
        uuid=uuid,
        new_item_name="transcription_status",
        new_item_value=new_status,
    )


def create_ddb_entry(table_name: str, uuid: str, media_uri: str, username: str):
    """Create a new entry in dynamodb, with timestamp"""

    dyn_resource = boto3.resource("dynamodb")
    # TODO: make sure it exists or something?
    table = dyn_resource.Table(name=table_name)

    # Why isn't this working?
    return table.put_item(
        Item={
            "UUID": uuid,
            "username": username,
            "media_uri": media_uri,
            "job_creation_time": str(datetime.datetime.now()),
            "media_name": os.path.split(media_uri)[-1],
        }
    )


def extract_username_from_s3_URI(uri: str) -> str:
    """URIs are like s3://bucket/blah/username/file_they_uploaded.mp4
    Return username
    TODO: test for security flaws, if filenames can contain / character"""
    return os.path.split(uri)[0].split("/")[-1]
