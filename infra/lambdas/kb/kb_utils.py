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
from typing import Generator, Dict, Any

from bedrock.bedrock_utils import get_bedrock_client
from kb.kb_qa_prompt import KB_QA_MESSAGE_TEMPLATE, KB_QA_SYSTEM_PROMPT

logger = logging.getLogger()
logger.setLevel("DEBUG")


class KBRetriever:
    def __init__(self, knowledge_base_id: str, region_name: str, num_chunks: int):
        self.knowledge_base_id = knowledge_base_id
        self.num_chunks = num_chunks
        self.bedrock_agent_runtime_client = get_bedrock_client(
            region=region_name, agent=True
        )

    def retrieve(self, query: str, username: str, media_name: str = None):
        username_filter = {"equals": {"key": "username", "value": username}}
        retrieval_filter = (
            username_filter
            if not media_name
            else {
                "andAll": [
                    username_filter,
                    {"equals": {"key": "media_name", "value": media_name}},
                ]
            }
        )

        retrieval_config = {
            "vectorSearchConfiguration": {
                "numberOfResults": int(self.num_chunks),
                "filter": retrieval_filter,
            },
        }

        return self.bedrock_agent_runtime_client.retrieve(
            knowledgeBaseId=self.knowledge_base_id,
            retrievalConfiguration=retrieval_config,
            retrievalQuery={"text": query},
        )


class LLMGenerator:
    def __init__(
        self,
        foundation_model: str,
        temperature: float,
        max_tokens: int,
        region_name: str,
    ):
        self.foundation_model = foundation_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.bedrock_client = get_bedrock_client(region=region_name, agent=False)

    def generate(
        self, messages: list, retrieval_response: dict, prompt_builder: "PromptBuilder"
    ):
        message_content = prompt_builder.build_full_prompt(
            query=messages[-1]["content"][0]["text"],
            chunks=prompt_builder.build_chunks_string(retrieval_response),
            conversation_context=prompt_builder.build_conversation_context(messages),
        )

        converse_kwargs = self._build_converse_kwargs(messages, message_content)
        response = self.bedrock_client.converse(**converse_kwargs)
        return response["output"]["message"]["content"][0]["text"]

    def generate_stream(
        self, messages: list, retrieval_response: dict, prompt_builder: "PromptBuilder"
    ):
        message_content = prompt_builder.build_full_prompt(
            query=messages[-1]["content"][0]["text"],
            chunks=prompt_builder.build_chunks_string(retrieval_response),
            conversation_context=prompt_builder.build_conversation_context(messages),
        )

        converse_kwargs = self._build_converse_kwargs(messages, message_content)
        response = self.bedrock_client.converse_stream(**converse_kwargs)
        return response.get("stream")

    def _build_converse_kwargs(self, messages: list, message_content: str):
        return {
            "system": [{"text": KB_QA_SYSTEM_PROMPT}],
            "modelId": self.foundation_model,
            "messages": messages[:-1]
            + [{"role": "user", "content": [{"text": message_content}]}],
            "inferenceConfig": {
                "temperature": self.temperature,
                "maxTokens": self.max_tokens,
            },
        }


class PromptBuilder:
    @staticmethod
    def build_chunks_string(retrieve_response: dict) -> str:
        chunks_string = ""
        for i, chunk in enumerate(retrieve_response["retrievalResults"]):
            chunks_string += f"<chunk_{i + 1}>\n<media_name>\n{chunk['metadata']['media_name']}\n</media_name>\n<transcript>\n{chunk['content']['text']}\n</transcript>\n</chunk_{i + 1}>\n\n"
        return chunks_string

    @staticmethod
    def build_conversation_context(messages: list) -> str:
        return "".join(
            f"{message['role']}: {message['content'][0]['text']}\n"
            for message in messages
        )

    @staticmethod
    def build_full_prompt(query: str, chunks: str, conversation_context: str) -> str:
        return KB_QA_MESSAGE_TEMPLATE.format(
            query=query,
            chunks=chunks,
            conversation_context=conversation_context,
        )


class ResponseProcessor:
    @staticmethod
    def postprocess_generation(generation_response_string: str) -> dict:
        pattern = r"<json>\s*(.*?)\s*</json>"
        matches = re.findall(pattern, generation_response_string, re.DOTALL)
        if not matches:
            raise ValueError("No JSON data found between <json> and </json> tags")

        match = matches[0].strip("\n")
        try:
            return json.loads(match)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")

    @staticmethod
    def postprocess_generation_stream(
        stream: Generator[Dict[str, Any], None, None],
    ) -> Generator[dict, None, None]:
        full_generated_string = ""
        # current_answer = {"answer": []}
        # current_partial_answer_index = 0

        for event in stream:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]["delta"].get("text", "")
                full_generated_string += delta

                yield ResponseProcessor.generated_string_to_dict(full_generated_string)

        yield ResponseProcessor.generated_string_to_dict(full_generated_string)

    @staticmethod
    def generated_string_to_dict(generated_string: str) -> dict:
        """Given the growing LLM string, attempt to parse as much of the response as possible
        into a json object matching the FullQAnswer object. This is some really tricky regex, all
        designed to give the best user experience possible. Partial answers should update continuously,
        citations don't get added to the output until they are fully formed"""
        result = {"answer": []}

        # Extract content between <json> tags, or everything after <json> if </json> is not present
        match = re.search(r"<json>(.*?)(?:</json>|$)", generated_string, re.DOTALL)
        if not match:
            return result

        json_content = match.group(1).strip()

        # Split the content into individual answer items
        answer_items = re.split(r"(?<=}),\s*{", json_content)

        for item in answer_items:
            current_item = {"partial_answer": "", "citations": []}

            # Extract partial_answer
            partial_answer_match = re.search(
                r'"partial_answer"\s*:\s*"(.*?)(?:"|$)', item, re.DOTALL
            )
            if partial_answer_match:
                current_item["partial_answer"] = (
                    partial_answer_match.group(1).replace("\n", " ").strip()
                )

            # Extract citations
            citations_match = re.search(r'"citations"\s*:\s*(\[.*?\])', item)
            if citations_match:
                try:
                    citations = json.loads(citations_match.group(1))
                    if all("media_name" in c and "timestamp" in c for c in citations):
                        current_item["citations"] = citations
                except json.JSONDecodeError:
                    pass

            result["answer"].append(current_item)

        return result


class RetrievalStrategy:
    def get_retrieval_response(
        self, retriever, query, username, media_name, full_transcript=None
    ):
        raise NotImplementedError


class ChunkingStrategy(RetrievalStrategy):
    def get_retrieval_response(
        self, retriever, query, username, media_name, full_transcript=None
    ):
        return retriever.retrieve(query, username, media_name)


class NoChunkingStrategy(RetrievalStrategy):
    def get_retrieval_response(
        self, retriever, query, username, media_name, full_transcript=None
    ):
        return {
            "retrievalResults": [
                {
                    "metadata": {"media_name": media_name},
                    "content": {"text": full_transcript},
                }
            ]
        }


class KBQARAG:
    def __init__(
        self,
        knowledge_base_id: str,
        region_name: str = "us-east-1",
        num_chunks: int = 5,
        foundation_model: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
        temperature=0,
        max_tokens=4096,
    ):
        self.retriever = KBRetriever(knowledge_base_id, region_name, num_chunks)
        self.generator = LLMGenerator(
            foundation_model, temperature, max_tokens, region_name
        )
        self.prompt_builder = PromptBuilder()
        self.response_processor = ResponseProcessor()

    def retrieve_and_generate_answer(
        self,
        messages: list,
        username: str,
        media_name: str = None,
        strategy: RetrievalStrategy = ChunkingStrategy(),
        full_transcript: str = None,
    ) -> dict:
        query = messages[-1]["content"][0]["text"]
        retrieval_response = strategy.get_retrieval_response(
            self.retriever, query, username, media_name, full_transcript
        )
        generation_response = self.generator.generate(
            messages, retrieval_response, self.prompt_builder
        )
        return self.response_processor.postprocess_generation(generation_response)

    def retrieve_and_generate_answer_stream(
        self,
        messages: list,
        username: str,
        media_name: str = None,
        strategy: RetrievalStrategy = ChunkingStrategy(),
        full_transcript: str = None,
    ) -> Generator[dict, None, None]:
        query = messages[-1]["content"][0]["text"]
        retrieval_response = strategy.get_retrieval_response(
            self.retriever, query, username, media_name, full_transcript
        )
        generation_response = self.generator.generate_stream(
            messages, retrieval_response, self.prompt_builder
        )
        return self.response_processor.postprocess_generation_stream(
            generation_response
        )

    def generate_answer_no_chunking(
        self, messages: list, media_name: str, full_transcript: str
    ) -> dict:
        strategy = NoChunkingStrategy()
        return self.retrieve_and_generate_answer(
            messages, "", media_name, strategy=strategy, full_transcript=full_transcript
        )

    def generate_answer_no_chunking_stream(
        self, messages: list, media_name: str, full_transcript: str
    ) -> Generator[dict, None, None]:
        strategy = NoChunkingStrategy()
        return self.retrieve_and_generate_answer_stream(
            messages, "", media_name, strategy=strategy, full_transcript=full_transcript
        )
