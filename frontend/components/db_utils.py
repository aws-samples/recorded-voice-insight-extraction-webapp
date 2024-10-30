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

import pandas as pd
import json
import os
import requests

BACKEND_API_URL = os.environ["BACKEND_API_URL"]


def retrieve_all_items(
    username: str, max_rows: int | None, api_auth_token: str
) -> pd.DataFrame:
    """Query dynamodb table for rows from this username and return
    specific columns w/ optional max # of rows"""

    json_body = {
        "action": "retrieve_all_items",
        "username": username,
        "max_rows": max_rows,
    }
    response = requests.post(
        BACKEND_API_URL + "/ddb",
        json=json_body,
        headers={"Authorization": api_auth_token},
        timeout=10,
    )
    if response.status_code != 200:
        raise Exception(f"Non 200 response from API gateway: {response.reason}")

    result = response.json()

    # Lambda returns json, convert to dataframe for UI
    if not result:
        # If no results at all in the DB (user hasn't uploaded anything yet),
        # return an empty dataframe with the right columns so user at least sees
        # what they should expect
        return pd.DataFrame(
            {"media_name": [], "job_creation_time": [], "job_status": []}
        )

    result_df = (
        pd.DataFrame.from_records(result)
        .sort_values("job_creation_time", ascending=False)
        .reset_index(drop=True)
    )

    return result_df if not max_rows else result_df.head(n=max_rows)


def retrieve_analysis_by_jobid(
    job_id: str, username: str, template_id: int, api_auth_token: str
) -> str | None:
    """Retrieve analysis from dynamodb table by job_id
    (if analysis is cached, else none)"""

    json_body = {
        "action": "retrieve_analysis_by_jobid",
        "job_id": job_id,
        "username": username,
        "template_id": int(template_id),
    }
    response = requests.post(
        BACKEND_API_URL + "/ddb",
        json=json_body,
        headers={"Authorization": api_auth_token},
        timeout=10,
    )
    if response.status_code != 200:
        raise Exception(f"Non 200 response from API gateway: {response.reason}")

    result = response.json()
    return result


def store_analysis_result(
    job_id: str,
    username: str,
    template_id: int,
    analysis_result: str,
    api_auth_token: str,
) -> str | None:
    """Store completed analysis in dynamodb table"""

    json_body = {
        "action": "store_analysis_result",
        "job_id": job_id,
        "username": username,
        "template_id": int(template_id),
        "analysis_result": analysis_result,
    }
    response = requests.post(
        BACKEND_API_URL + "/ddb",
        json=json_body,
        headers={"Authorization": api_auth_token},
        timeout=10,
    )
    if response.status_code != 200:
        raise Exception(f"Non 200 response from API gateway: {response.reason}")

    result = response.json()
    return result
