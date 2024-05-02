# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for working with Amazon Bedrock"""

import json
import logging
import os
from typing import Optional

import boto3
import pandas as pd
from botocore.config import Config

logger = logging.getLogger("MASstack")
logger.setLevel(logging.INFO)
if not logger.handlers:
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)


def get_bedrock_client(
    assumed_role: Optional[str] = None,
    region: Optional[str] = None,
    runtime: Optional[bool] = True,
):
    """Create a boto3 client for Amazon Bedrock, with optional configuration overrides

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

    if runtime:
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
        """Generate using message API"""

        logger.debug("BEGIN Prompt\n" + "=" * 20)
        logger.debug(prompt)
        logger.debug("END Prompt\n" + "=" * 20)

        body = {
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
            "anthropic_version": "",
            **kwargs,
        }
        logger.info(f"body = {body}")

        response = self.boto3_bedrock.invoke_model(
            modelId=model_id, body=json.dumps(body)
        )
        response = json.loads(response["body"].read().decode("utf-8"))

        completion = response["content"][0]["text"]

        logger.debug("BEGIN Completion\n" + "=" * 20)
        logger.debug(completion)
        logger.debug("END Completion\n" + "=" * 20)

        return completion


def get_analysis_templates() -> pd.DataFrame:
    """Read analysis templates (from csv for now, from db later) and return df"""
    dirname = os.path.dirname(__file__)  # Location of this python file
    analysis_templates_file_fullpath = os.path.join(
        dirname, "../assets/analysis_templates.csv"
    )
    return pd.read_csv(analysis_templates_file_fullpath)


def run_analysis(analysis_id: int, transcript: str, llm: LLM):
    # Get analysis template from csv
    template_df = get_analysis_templates()
    ana_series = template_df.set_index("template_id").loc[analysis_id]
    # Build prompt, set model ID, bedrock kwargs, etc
    system_prompt = ana_series["template_system_prompt"]
    ana_template = ana_series["template_string"]
    ana_prompt = ana_template.format(transcript=transcript)
    ana_kwargs = json.loads(ana_series["bedrock_kwargs"])
    ana_model_id = ana_series["model_id"]
    # Inference LLM & return result
    return llm.generate(
        model_id=ana_model_id,
        system_prompt=system_prompt,
        prompt=ana_prompt,
        kwargs=ana_kwargs,
    )
