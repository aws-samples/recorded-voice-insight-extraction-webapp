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

import os
import json
import requests
from requests.exceptions import RequestException

BACKEND_API_URL = os.environ["BACKEND_API_URL"]


def retrieve_transcript_by_jobid(
    job_id: str, username: str, api_auth_id_token: str
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
        headers={"Authorization": api_auth_id_token},
        timeout=5,
    )
    if response.status_code != 200:
        raise Exception(
            f"Error getting presigned URL from API gateway: {response.reason}"
        )

    presigned_url = response.json()

    # 2. Use requests to GET from the presigned URL the transcript txt
    http_response = requests.get(presigned_url, timeout=5)
    # If successful, returns HTTP status code 200
    if http_response.status_code != 200:
        raise Exception(
            f"Error downloading transcript from s3, status code: {http_response.status_code}"
        )

    # 3. Return the transcript txt
    return http_response.text


def retrieve_subtitles_by_jobid(
    job_id: str,
    username: str,
    api_auth_id_token: str,
    translation_start_time: int | None = None,
    translation_duration: int | None = None,
    translation_destination_language: str | None = None,
) -> str:
    """Retrieve subtitles (vtt format) for a file via the job_id.
    Optional parameters to translate a portion of them to a
    new language."""

    json_body = {
        "username": username,
        "transcript_job_id": job_id,
    }
    if translation_start_time:
        json_body["translation_start_time"] = translation_start_time
    if translation_duration:
        json_body["translation_duration"] = translation_duration
    if translation_destination_language:
        json_body["translation_destination_language"] = translation_destination_language

    try:
        response = requests.post(
            BACKEND_API_URL + "/subtitles",
            json=json_body,
            headers={"Authorization": api_auth_id_token},
            timeout=29,
        )
        # This will raise an HTTPError for any 4XX or 5XX status
        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError as e:
        # This exception is only raised by raise_for_status()
        # So response is guaranteed to exist here
        if response.status_code == 503:
            raise RequestException(
                f"Throttling error received from translation job: {response.reason}"
            ) from e
        else:
            raise Exception(
                f"Error getting subtitles from API gateway: {response.reason}"
            ) from e
    except requests.exceptions.RequestException as e:
        # Handle other request-related exceptions (ConnectionError, Timeout, etc.)
        raise Exception(f"Request error: {str(e)}") from e
    except Exception as e:
        # Handle any other unexpected exceptions
        raise Exception(f"Unexpected error: {str(e)}") from e


def retrieve_media_url(media_name: str, username: str, api_auth_id_token: str) -> str:
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
        headers={"Authorization": api_auth_id_token},
        timeout=5,
    )
    if response.status_code != 200:
        raise Exception(
            f"Error getting presigned URL from API gateway: {response.reason}"
        )

    presigned_url = response.json()

    # 2. Return the presigned URL directly
    return presigned_url


def upload_to_s3(fileobj, filename: str, username: str, api_auth_id_token: str) -> bool:
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
        headers={"Authorization": api_auth_id_token},
        timeout=5,
    )
    if response.status_code != 200:
        raise Exception(
            f"Error getting presigned URL from API gateway: {response.reason}"
        )
    presigned_url_details = response.json()

    # 2. Use requests to POST the file directly to s3 via presigned url
    files = {"file": (filename, fileobj)}
    http_response = requests.post(
        presigned_url_details["url"],
        data=presigned_url_details["fields"],
        files=files,
        timeout=30,
    )
    # If successful, returns HTTP status code 204
    if http_response.status_code != 204:
        raise Exception(
            f"Error uploading to s3, status code: {http_response.status_code}"
        )

    return True


def delete_file_by_jobid(
    job_id: str,
    username: str,
    api_auth_id_token: str,
) -> str:
    """Permanently delete uploaded file (and re-sync knowledge base)"""

    json_body = {
        "username": username,
        "job_id": job_id,
    }

    response = requests.post(
        BACKEND_API_URL + "/kb-job-deletion",
        json=json_body,
        headers={"Authorization": api_auth_id_token},
        timeout=29,
    )
    if response.status_code != 200:
        raise Exception(f"Error deleting file: {response.reason}")

    return response.json()
