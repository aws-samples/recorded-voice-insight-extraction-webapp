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

"""Utilities related to accessing dynamoDB"""

import boto3
import pandas as pd
from boto3.dynamodb.conditions import Key
import os

TABLE_NAME = os.environ["ddb_table_name"]
dyn_resource = boto3.resource("dynamodb")
table = dyn_resource.Table(name=TABLE_NAME)


def retrieve_all_items(username, max_rows=None) -> pd.DataFrame:
    """Query dynamodb table for rows from this username and return
    specific columns w/ optional max # of rows"""

    query_results = table.query(KeyConditionExpression=Key("username").eq(username))[
        "Items"
    ]
    if not query_results:
        # If no results at all in the DB (user hasn't uploaded anything yet),
        # return an empty dataframe with the right columns so user at least sees
        # what they should expect
        return pd.DataFrame(
            {"media_name": [], "job_creation_time": [], "transcription_status": []}
        )

    result_df = (
        pd.DataFrame.from_records(query_results)
        .sort_values("job_creation_time", ascending=False)
        .reset_index(drop=True)
    )

    return result_df if not max_rows else result_df.head(n=max_rows)


def template_id_to_dynamo_field_name(template_id: int) -> str:
    return f"llm_analysis_template_{template_id}"


def retrieve_analysis_by_jobid(
    job_id: str, username: str, template_id: int
) -> str | None:
    """Retrieve analysis from dynamodb table by job_id
    (if analysis is cached, else none)"""

    llm_ana_key = template_id_to_dynamo_field_name(template_id)
    response = table.get_item(
        Key={"username": username, "UUID": job_id}, ProjectionExpression=llm_ana_key
    )["Item"]
    try:
        return response[llm_ana_key]
    except KeyError:
        return None


def store_analysis_result(
    job_id: str, username: str, template_id: int, analysis_result: str
) -> str | None:
    """Store completed analysis in dynamodb table"""

    llm_ana_key = template_id_to_dynamo_field_name(template_id)

    table.update_item(
        Key={"username": username, "UUID": job_id},
        UpdateExpression="SET #new_attr = :new_value",
        ExpressionAttributeNames={"#new_attr": llm_ana_key},
        ExpressionAttributeValues={":new_value": analysis_result},
    )

    return
