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

"""Base data models for LLM Q&A responses"""

from pydantic import BaseModel
from typing import List
import re
import json


class Citation(BaseModel):
    media_name: str
    timestamp: int


class PartialQAnswer(BaseModel):
    partial_answer: str
    citations: List[Citation]

    def pprint(self):
        print(f"LLMAnswer:\n Answer={self.answer}\n Citations={self.citations}")


class FullQAnswer(BaseModel):
    answer: List[PartialQAnswer]

    @classmethod
    def from_LLM_response(cls, generation_response: str) -> "FullQAnswer":
        """
        Create a FullQAnswer instance from an LLM response string containing JSON data.

        The JSON data should be enclosed between <json> and </json> tags.
        """
        print(f"generation_response={generation_response}")
        pattern = r"<json>\s*(.*?)\s*</json>"
        matches = re.findall(pattern, generation_response, re.DOTALL)
        if not matches:
            raise ValueError("No JSON data found between <json> and </json> tags")

        match = matches[0].strip("\n")
        try:
            data = json.loads(match)
            return cls(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")
        except ValueError as e:
            raise ValueError(f"Error creating FullQAnswer instance: {e}")

    def get_first_citation(self):
        """Return the first citation from any partial answers (utility fn for UI)"""
        for partial in self.answer:
            if partial.citations:
                return partial.citations[0]
        raise ValueError("No citations found in any partial answers")

    def pprint(self) -> str:
        """Format the FullQAnswer to a string for display by a chatbot"""
        result = ""
        citation_counter = 1

        for partial in self.answer:
            result += partial.partial_answer
            for _citation in partial.citations:
                result += f"[{citation_counter}]"
                citation_counter += 1
        return result
