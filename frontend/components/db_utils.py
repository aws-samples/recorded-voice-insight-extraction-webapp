"""Utilities related to accessing dynamoDB"""

import boto3
import pandas as pd
from boto3.dynamodb.conditions import Key

TABLE_NAME = "ReVIEW-App-Table"
dyn_resource = boto3.resource("dynamodb")
table = dyn_resource.Table(name=TABLE_NAME)


def retrieve_all_items(username, max_rows=None) -> pd.DataFrame:
    """Scan entire dynamodb table for rows from this username and return
    specific columns w/ optional max # of rows"""
    # TODO: replace this with query function instead of scan, query by username
    # Maybe set username as primary key or partition index something?
    scan_kwargs = {
        "FilterExpression": Key("username").eq(username),
        "ProjectionExpression": "media_name, job_creation_time, transcription_status, #foo",
        "ExpressionAttributeNames": {"#foo": "UUID"},
    }

    scan_results = table.scan(**scan_kwargs)["Items"]
    if not scan_results:
        # If no results at all in the DB (user hasn't uploaded anything yet),
        # return an empty dataframe with the right columns so user at least sees
        # what they should expect
        return pd.DataFrame(
            {"media_name": [], "job_creation_time": [], "transcription_status": []}
        )

    result_df = (
        pd.DataFrame.from_records(scan_results)
        .sort_values("job_creation_time", ascending=False)
        .reset_index(
            drop=True
        )  # [["job_creation_time", "media_name", "transcription_status"]]
    )

    return result_df if not max_rows else result_df.head(n=max_rows)


def template_id_to_dynamo_field_name(template_id: int) -> str:
    return f"llm_analysis_template_{template_id}"


def retrieve_analysis_by_jobid(job_id: str, template_id: int) -> str | None:
    """Retrieve analysis from dynamodb table by job_id
    (if analysis is cached, else none)"""

    llm_ana_key = template_id_to_dynamo_field_name(template_id)
    response = table.get_item(Key={"UUID": job_id}, ProjectionExpression=llm_ana_key)[
        "Item"
    ]
    try:
        return response[llm_ana_key]
    except KeyError:
        return None


def store_analysis_result(
    job_id: str, template_id: int, analysis_result: str
) -> str | None:
    """Store completed analysis in dynamodb table"""

    llm_ana_key = template_id_to_dynamo_field_name(template_id)

    table.update_item(
        Key={"UUID": job_id},
        UpdateExpression="SET #new_attr = :new_value",
        ExpressionAttributeNames={"#new_attr": llm_ana_key},
        ExpressionAttributeValues={":new_value": analysis_result},
    )

    return
