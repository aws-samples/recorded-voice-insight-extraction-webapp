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

"""Utils related to accessing Bedrock"""

import json
import logging
import os
from typing import Optional

import boto3
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel("INFO")


def get_bedrock_client(
    assumed_role: Optional[str] = None,
    region: Optional[str] = None,
    runtime: Optional[bool] = True,
    agent: Optional[bool] = False,
):
    """Create a boto3 client for Amazon Bedrock or for Amazon Bedrock Agents,
    with optional configuration overrides

    Parameters
    ----------
    assumed_role :
        Optional ARN of an AWS IAM role to assume for calling the Bedrock service. If not
        specified, the current active credentials will be used.
    region :
        Optional name of the AWS Region in which the service should be called (e.g. "us-east-1").
        If not specified, AWS_REGION or AWS_DEFAULT_REGION environment variable will be used.
    runtime :
        Optional choice of getting different client to perform operations with the Amazon Bedrock service.
    agent :
        Return a bedrock-agent-runtime client instead of bedrock or bedrock-runtime
    """
    if region is None:
        target_region = os.environ.get(
            "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION")
        )
    else:
        target_region = region

    logger.info(f"Create new client\n  Using region: {target_region}")
    session_kwargs = {"region_name": target_region}
    client_kwargs = {**session_kwargs}

    profile_name = os.environ.get("AWS_PROFILE")
    if profile_name:
        logger.info(f"  Using profile: {profile_name}")
        session_kwargs["profile_name"] = profile_name

    retry_config = Config(
        region_name=target_region,
        retries={
            "max_attempts": 1,
            "mode": "standard",
        },
        read_timeout=300,  # 5 min read timeout
    )
    session = boto3.Session(**session_kwargs)

    if assumed_role:
        logger.info(f"  Using role: {assumed_role}", end="")
        sts = session.client("sts")
        response = sts.assume_role(
            RoleArn=str(assumed_role), RoleSessionName="langchain-llm-1"
        )
        logger.info(" ... successful!")
        client_kwargs["aws_access_key_id"] = response["Credentials"]["AccessKeyId"]
        client_kwargs["aws_secret_access_key"] = response["Credentials"][
            "SecretAccessKey"
        ]
        client_kwargs["aws_session_token"] = response["Credentials"]["SessionToken"]

    if agent:
        service_name = "bedrock-agent-runtime"
    elif runtime:
        service_name = "bedrock-runtime"
    else:
        service_name = "bedrock"

    bedrock_client = session.client(
        service_name=service_name, config=retry_config, **client_kwargs
    )

    logger.info("boto3 Bedrock client successfully created!")
    logger.info(f"{bedrock_client._endpoint=}")
    return bedrock_client


class LLM:
    """Class to invoke Bedrock foundation models for generation (messages API)"""

    def __init__(self):
        self.accept = "application/json"
        self.content_type = "application/json"
        self.boto3_bedrock = get_bedrock_client(
            assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None),
            region=os.environ.get("AWS_DEFAULT_REGION", None),
        )

    def generate(
        self, model_id: str, system_prompt: str, prompt: str, kwargs: dict = {}
    ) -> str:
        """Generate using Converse API for better model compatibility"""

        logger.debug("BEGIN Prompt\n" + "=" * 20)
        logger.debug(prompt)
        logger.debug("END Prompt\n" + "=" * 20)

        # Build inference config from kwargs
        inference_config = {}
        
        # Map common parameters to Converse API format
        if "temperature" in kwargs:
            inference_config["temperature"] = kwargs["temperature"]
        if "maxTokens" in kwargs:
            inference_config["maxTokens"] = kwargs["maxTokens"]
        if "topP" in kwargs:
            inference_config["topP"] = kwargs["topP"]
        if "stopSequences" in kwargs:
            inference_config["stopSequences"] = kwargs["stopSequences"]

        # Build the converse request
        converse_kwargs = {
            "modelId": model_id,
            "system": [{"text": system_prompt}],
            "messages": [
                {"role": "user", "content": [{"text": prompt}]}
            ],
            "inferenceConfig": inference_config
        }

        logger.info(f"converse_kwargs = {converse_kwargs}")

        response = self.boto3_bedrock.converse(**converse_kwargs)
        
        completion = response["output"]["message"]["content"][0]["text"]

        logger.debug("BEGIN Completion\n" + "=" * 20)
        logger.debug(completion)
        logger.debug("END Completion\n" + "=" * 20)

        return completion
