import datetime
from typing import Any

import boto3


def update_ddb_entry(
    table_name: str, uuid: str, new_item_name: str, new_item_value: Any
):
    """Update an existing item in the dynamodb"""

    dyn_resource = boto3.resource("dynamodb")
    # TODO: make sure it exists or something?
    table = dyn_resource.Table(name=table_name)

    return table.update_item(
        Key={"UUID": uuid},
        UpdateExpression="SET #new_attr = :new_value",
        ExpressionAttributeNames={"#new_attr": new_item_name},
        ExpressionAttributeValues={":new_value": new_item_value},
    )


def create_ddb_entry(table_name: str, uuid: str, media_uri: str):
    """Create a new entry in dynamodb, witih timestamp"""

    dyn_resource = boto3.resource("dynamodb")
    # TODO: make sure it exists or something?
    table = dyn_resource.Table(name=table_name)

    return table.put_item(
        Item={
            "UUID": uuid,
            "media_uri": media_uri,
            "job_creation_time": str(datetime.datetime.now()),
        }
    )
