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


import os


def extract_username_from_s3_URI(uri: str) -> str:
    """URIs are like s3://bucket/blah/username/file_they_uploaded.mp4
    Return username
    TODO: test for security flaws, e.g. if usernames can contain / character"""
    return os.path.split(uri)[0].split("/")[-1]


def extract_uuid_from_s3_URI(uri: str) -> str:
    """URIs are like s3://bucket/blah/username/[uuid].txt.metadata.json
    Return uuid"""
    return os.path.split(uri)[-1].split(".")[0]


def build_kb_metadata_json(username: str, media_name: str) -> dict:
    """Custom metadata for bedrock knowledge base to grab and include in OpenSearch for filtering"""
    return {"metadataAttributes": {"username": username, "media_name": media_name}}
