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

"""Utilities related to accessing s3"""

import json
import os

import requests

BACKEND_API_URL = os.environ["BACKEND_API_URL"]


def retrieve_transcript_by_jobid(
    job_id: str, username: str, api_auth_token: str
) -> str:
    """Get presigned URL to download transcript from s3, download it, return str"""
    # Download transcript txt file workflow

    # 1. Get a presigned URL from API Gateway to download the transcript
    json_body = {
        "action": "download_transcript_txt_file",
        "username": username,
        "job_id": job_id,
    }
    response = requests.post(
        BACKEND_API_URL + "/s3-presigned",
        json=json_body,
        headers={"Authorization": api_auth_token},
    )
    if response.status_code != 200:
        raise Exception(
            f"Error getting presigned URL from API gateway: {response.reason}"
        )

    presigned_url = json.loads(response.text)

    # 2. Use requests to GET from the presigned URL the transcript txt
    http_response = requests.get(presigned_url)
    # If successful, returns HTTP status code 200
    if http_response.status_code != 200:
        raise Exception(
            f"Error downloading transcript from s3, status code: {http_response.status_code}"
        )

    # 3. Return the transcript txt
    return http_response.text


def retrieve_media_url(media_name: str, username: str, api_auth_token: str) -> str:
    """Get presigned URL to view media in s3, return URL"""
    # Download media file workflow

    # 1. Get a presigned URL from API Gateway to download the media file
    json_body = {
        "action": "download_media_file",
        "username": username,
        "media_file_name": media_name,
    }
    response = requests.post(
        BACKEND_API_URL + "/s3-presigned",
        json=json_body,
        headers={"Authorization": api_auth_token},
    )
    if response.status_code != 200:
        raise Exception(
            f"Error getting presigned URL from API gateway: {response.reason}"
        )

    presigned_url = json.loads(response.text)

    # 2. Return the presigned URL directly
    return presigned_url


def upload_to_s3(fileobj, filename: str, username: str, api_auth_token: str) -> bool:
    """Get presigned URL to upload to s3, then upload"""
    # Upload media file workflow

    # 1. Get a presigned URL from API Gateway to upload the media file
    json_body = {
        "action": "upload_media_file",
        "username": username,
        "media_file_name": filename,
    }
    response = requests.post(
        BACKEND_API_URL + "/s3-presigned",
        json=json_body,
        headers={"Authorization": api_auth_token},
    )
    if response.status_code != 200:
        raise Exception(
            f"Error getting presigned URL from API gateway: {response.reason}"
        )
    presigned_url_details = json.loads(response.text)

    # 2. Use requests to POST the file directly to s3 via presigned url
    files = {"file": (filename, fileobj)}
    http_response = requests.post(
        presigned_url_details["url"], data=presigned_url_details["fields"], files=files
    )
    # If successful, returns HTTP status code 204
    if http_response.status_code != 204:
        raise Exception(
            f"Error uploading to s3, status code: {http_response.status_code}"
        )

    return True
