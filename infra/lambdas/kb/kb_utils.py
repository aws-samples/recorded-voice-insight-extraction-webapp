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


"""Utilities related to querying Bedrock knowledge bases."""

import json
import logging
import re
from bedrock.bedrock_utils import get_bedrock_client
from kb.kb_qa_prompt import KB_QA_MESSAGE_TEMPLATE, KB_QA_SYSTEM_PROMPT

logger = logging.getLogger()
logger.setLevel("DEBUG")


class KBQARAG:
    """Class to handle querying Bedrock KB for QA RAG workflows"""

    def __init__(
        self,
        knowledge_base_id: str,
        region_name: str = "us-east-1",
        num_chunks: int = 5,
        foundation_model: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
        temperature=0,
        max_tokens=5000,
    ):
        self.FOUNDATION_MODEL = foundation_model
        self.REGION_NAME = region_name
        self.KNOWLEDGE_BASE_ID = knowledge_base_id
        self.NUM_CHUNKS = int(num_chunks)
        self.TEMPERATURE = temperature
        self.MAX_TOKENS = max_tokens

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

    @staticmethod
    def _postprocess_generation(generation_response: str) -> str:
        """Extract json content so response can be parsed into FullQAnswer object"""
        pattern = r"<json>\s*(.*?)\s*</json>"
        matches = re.findall(pattern, generation_response, re.DOTALL)
        if not matches:
            raise ValueError("No JSON data found between <json> and </json> tags")

        match = matches[0].strip("\n")
        try:
            json_data = json.loads(match)
            return json_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")
        except ValueError as e:
            raise ValueError(f"Error creating FullQAnswer instance: {e}")

    def _generate(self, query, retrieval_response, **kwargs) -> str:
        """Generate string from LLM"""
        chunks_str = self._build_chunks_string(retrieval_response)

        message_content = KB_QA_MESSAGE_TEMPLATE.format(query=query, chunks=chunks_str)

        body = {
            "system": KB_QA_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": message_content}],
            "anthropic_version": "",
            "temperature": self.TEMPERATURE,
            "max_tokens": self.MAX_TOKENS,
            **kwargs,
        }
        response = self.bedrock_client.invoke_model(
            modelId=self.FOUNDATION_MODEL, body=json.dumps(body)
        )

        response = json.loads(response["body"].read().decode("utf-8"))["content"][0][
            "text"
        ]

        return response

    def retrieve_and_generate_answer(
        self, query: str, username: str, media_name: str = None
    ) -> dict:
        """Retrieve from KB and generate json that can be parsed into FullQAnswer object"""
        retrieval_response = self._retrieve(query, username, media_name)
        generation_response = self._generate(
            query=query,
            retrieval_response=retrieval_response,
        )
        postprocessed_response = self._postprocess_generation(generation_response)
        # This is how frontend will parse this response into a FullQAnswer object
        # answer: FullQAnswer = FullQAnswer(**postprocessed_response)
        return postprocessed_response

    def generate_answer_no_chunking(
        self, query: str, media_name: str, full_transcript: str
    ) -> dict:
        """Bypass chunking by providing entire transcript as a single chunk to the prompt,
        return json which can be parsed into a FullQAnswer object"""

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
        postprocessed_response = self._postprocess_generation(generation_response)
        # This is how frontend will parse this response into a FullQAnswer object
        # answer: FullQAnswer = FullQAnswer(**postprocessed_response)
        return postprocessed_response
