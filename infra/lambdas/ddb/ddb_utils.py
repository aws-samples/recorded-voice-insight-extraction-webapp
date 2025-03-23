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

from boto3.dynamodb.conditions import Key
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


def _template_id_to_dynamo_field_name(template_id: int) -> str:
    return f"llm_analysis_template_{template_id}"


def retrieve_all_items(table, username) -> dict:
    """Query dynamodb table for rows from this username and return
    specific columns w/ optional max # of rows"""

    query_results = table.query(KeyConditionExpression=Key("username").eq(username))[
        "Items"
    ]

    return query_results


def retrieve_analysis_by_jobid(
    table, job_id: str, username: str, template_id: int
) -> str | None:
    """Retrieve analysis from dynamodb table by job_id
    (if analysis is cached, else none)"""

    llm_ana_key = _template_id_to_dynamo_field_name(template_id)
    response = table.get_item(
        Key={"username": username, "UUID": job_id}, ProjectionExpression=llm_ana_key
    )["Item"]
    try:
        return response[llm_ana_key]
    except KeyError:
        return None


def store_analysis_result(
    table, job_id: str, username: str, template_id: int, analysis_result: str
) -> str | None:
    """Store completed analysis in dynamodb table"""

    llm_ana_key = _template_id_to_dynamo_field_name(template_id)

    table.update_item(
        Key={"username": username, "UUID": job_id},
        UpdateExpression="SET #new_attr = :new_value",
        ExpressionAttributeNames={"#new_attr": llm_ana_key},
        ExpressionAttributeValues={":new_value": analysis_result},
    )

    return
