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

"""Helper utilities for working with Amazon Bedrock"""

import json
import logging
import os
from typing import Optional

import boto3
from botocore.config import Config

# Add frontend dir to system path to facilitate absolute import
import sys

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
    )
)

from schemas.qa_response import FullQAnswer

logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.handlers:
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)

KB_QA_SYSTEM_PROMPT = """You are an intelligent AI which attempts to answer questions based on retrieved chunks of automatically generated transcripts."""

KB_QA_MESSAGE_TEMPLATE = """
I will provide you with retrieved chunks of transcripts. The user will provide you with a question. Using only information in the provided transcript chunks, you will attempt to answer the user's question.

Each chunk will include a <media_name> block which contains the parent file that the transcript came from. Each line in the transcript chunk begins with an integer timestamp (in seconds) within square brackets, followed by a transcribed sentence. When answering the question, you will need to provide the timestamp you got the answer from.

Here are the retrieved chunks of transcripts in numbered order:

<transcript_chunks>
{chunks}
</transcript_chunks>

When you answer the question, your answer must include a parsable json string contained within <json></json> tags. The json should have one top level key, "answer", whose value is a list. Each element in the list represents a portion of the full answer, and should have two keys: "partial_answer", is a human readable part of your answer to the user's question, and "citations" which is a list of dicts which contain a "media_name" key and a "timestamp" key, which correspond to the resources used to answer that part of the question. For example, if you got this partial_answer from only one chunk, then the "citations" list will be only one element long, with the media_name of the chunk from which you got the partial_answer, and the relevant timestamp within that chunk's transcript. If you used information from three chunks for this partial_answer, the "citations" list will be three elements long. For multi-part answers, the partial_answer list will be multiple elements long.

The final answer displayed to the user will be all of the partial_answers concatenated. Make sure that you format your partial answers appropriately to make them human readable. For example, if your response has two partial answers which are meant to be displayed as a comma separated list, the first partial_answer should be formatted like "partial_answer": "The two partial answers are this" and the second partial_answer should be formatted like "partial_answer": ", and this.". Similarly, if your partial answers are meant to be a bulleted list, the first partial answer may look like "partial_answer": "The partial answers are:\\n- First partial answer" and "partial_answer": "\\n- Second partial answer". Note the newline character at the beginning of the second partial_answer for final display purposes. Do not include timestamps in your partial_answer strings, those are included only in the citation portions.

For example, if your answer is in two parts, the first part coming from two chunks, the second part coming from one chunk, your answer will have this structure:
<json>
{{"answer": [ {{"partial_answer": "This is the first part to the answer.", "citations": [{{"media_name": "media_file_foo.mp4", "timestamp": 123}}, {{"media_name": "media_file_bar.mp4", "timestamp": 345}}]}}, {{"partial_answer": " This is the second part to the answer.", "citations": [{{"media_name": "blahblah.wav", "timestamp": 83}}]}} ] }}
</json>

Notice the space at the beginning of the second partial_answer string, " This is...". That space is important so when the partial_answers get concatenated they will be readable, like "This is the first part to the answer. This is the second..."

If no transcript_chunks are provided or if you are unable to answer the question using information provided in any of the transcript_chunks, your response should include no citations like this:
<json>
{{"answer": [ {{"partial_answer": "I am unable to answer the question based on the provided media file(s).", "citations": []}} ] }}
</json>

Here is the user's question:
<question>
{query}
</question>

Now write your json response in <json> </json> brackets like explained above. Make sure the content between the brackets is json parsable, e.g. escaping " marks inside of strings and so on. Use this response if you are unable to definitively answer the question from the provided information:
<json>
{{"answer": [ {{"partial_answer": "I am unable to answer the question based on the provided media file(s).", "citations": []}} ] }}
</json>

Now write your answer:
"""


def get_bedrock_client(
    assumed_role: Optional[str] = None,
    region: Optional[str] = None,
    runtime: Optional[bool] = True,
    agent: Optional[bool] = False,
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


class KBQARAG:
    def __init__(
        self,
        knowledge_base_id: str,
        region_name: str = "us-east-1",
        num_chunks: int = 5,
        foundation_model: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
    ):
        self.FOUNDATION_MODEL = foundation_model
        self.REGION_NAME = region_name
        self.KNOWLEDGE_BASE_ID = knowledge_base_id
        self.NUM_CHUNKS = num_chunks
        # Used for retrieval
        self.bedrock_agent_runtime_client = get_bedrock_client(
            region=self.REGION_NAME, agent=True
        )

        # Used for generation
        self.bedrock_client = get_bedrock_client(region=self.REGION_NAME, agent=False)

    def _retrieve(self, query, username, media_name):
        # Always filter on username to prevent people from querying other users' data
        # Optionally filter on media name if user wants to chat with just one media file
        username_filter = {"equals": {"key": "username", "value": username}}
        if not media_name:
            retrieval_filter = username_filter
        else:
            retrieval_filter = {
                "andAll": [
                    username_filter,
                    {"equals": {"key": "media_name", "value": media_name}},
                ]
            }

        retrieval_config = {
            "vectorSearchConfiguration": {
                "numberOfResults": self.NUM_CHUNKS,
                "filter": retrieval_filter,
            },
        }

        res = self.bedrock_agent_runtime_client.retrieve(
            knowledgeBaseId=self.KNOWLEDGE_BASE_ID,
            retrievalConfiguration=retrieval_config,
            retrievalQuery={"text": query},
        )

        return res

    @staticmethod
    def _build_chunks_string(retrieve_response: dict) -> str:
        """Build a single string from retrieved chunks like:
        <chunk_1>
        <media_name>
        foo-bar-vid.mp4
        </media_name>
        <transcript>
        [0] blah blah [12] blah blah blah
        </transcript>
        </chunk_1>
        <chunk_2>
        ...
        """

        chunks_string = ""
        for i, chunk in enumerate(retrieve_response["retrievalResults"]):
            chunks_string += f"<chunk_{i+1}>\n<media_name>\n{chunk['metadata']['media_name']}\n</media_name>\n<transcript>\n{chunk['content']['text']}\n</transcript>\n</chunk_{i+1}>\n\n"
        return chunks_string

    def _generate(self, query, retrieval_response, **kwargs) -> str:
        chunks_str = self._build_chunks_string(retrieval_response)

        message_content = KB_QA_MESSAGE_TEMPLATE.format(query=query, chunks=chunks_str)

        body = {
            "system": KB_QA_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": message_content}],
            "anthropic_version": "",
            "temperature": 0,
            "max_tokens": 5000,
            **kwargs,
        }
        response = self.bedrock_client.invoke_model(
            modelId=self.FOUNDATION_MODEL, body=json.dumps(body)
        )

        response = json.loads(response["body"].read().decode("utf-8"))

        return response["content"][0]["text"]

    def retrieve_and_generate_answer(
        self, query: str, username: str, media_name: str = None
    ) -> FullQAnswer:
        print("Using full workflow!")
        retrieval_response = self._retrieve(query, username, media_name)
        generation_response = self._generate(
            query=query,
            retrieval_response=retrieval_response,
        )
        answer: FullQAnswer = FullQAnswer.from_LLM_response(generation_response)
        return answer

    def generate_answer_no_chunking(
        self, query: str, media_name: str, full_transcript: str
    ) -> FullQAnswer:
        """Bypass chunking by providing entire transcript as a single chunk to the prompt"""
        print("Bypassing chunking!!")
        mock_retrieval_response = {
            "retrievalResults": [
                {
                    "metadata": {"media_name": media_name},
                    "content": {"text": full_transcript},
                }
            ]
        }
        generation_response = self._generate(
            query=query,
            retrieval_response=mock_retrieval_response,
        )
        answer: FullQAnswer = FullQAnswer.from_LLM_response(generation_response)
        return answer


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
