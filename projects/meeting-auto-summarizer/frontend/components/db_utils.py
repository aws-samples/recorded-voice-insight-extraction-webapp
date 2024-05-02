"""Utilities related to accessing dynamoDB"""

import boto3
import pandas as pd

TABLE_NAME = "MAS-App-Table"
dyn_resource = boto3.resource("dynamodb")
table = dyn_resource.Table(name=TABLE_NAME)


def retrieve_all_items(max_rows=None) -> pd.DataFrame:
    """Scan entire dynamodb table and return some columns w/ optional max # of rows"""
    scan_kwargs = {
        # "FilterExpression": Key("year").between(year_range["first"], year_range["second"]),
        "ProjectionExpression": "media_name, job_creation_time, transcription_status, #foo",
        "ExpressionAttributeNames": {"#foo": "UUID"},
    }

    scan_results = table.scan(**scan_kwargs)
    result_df = (
        pd.DataFrame.from_records(scan_results["Items"])
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
