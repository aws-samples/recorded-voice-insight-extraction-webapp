import boto3
import pandas as pd

TABLE_NAME = "MAS-App-Table"
dyn_resource = boto3.resource("dynamodb")
table = dyn_resource.Table(name=TABLE_NAME)


def retrieve_all_items() -> pd.DataFrame:
    """Scan entire dynamodb table and return some columns"""
    scan_kwargs = {
        # "FilterExpression": Key("year").between(year_range["first"], year_range["second"]),
        "ProjectionExpression": "media_name, job_creation_time, transcription_status, #foo",
        "ExpressionAttributeNames": {"#foo": "UUID"},
    }

    scan_results = table.scan(**scan_kwargs)
    return (
        pd.DataFrame.from_records(scan_results["Items"])
        .sort_values("job_creation_time", ascending=False)
        .reset_index()[["job_creation_time", "media_name", "transcription_status"]]
    )
