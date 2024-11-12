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

"""Base data models for LLM Q&A responses with timestampped citations"""

from pydantic import BaseModel, Field
from typing import List, Optional


class Citation(BaseModel):
    """A single citation from a transcript"""

    media_name: str
    timestamp: int


class PartialQAnswer(BaseModel):
    """Part of a complete answer, to be concatenated with other partial answers"""

    partial_answer: str
    citations: Optional[List[Citation]] = Field(default_factory=list)

    def pprint(self):
        print(f"LLMAnswer:\n Answer={self.answer}\n Citations={self.citations}")


class FullQAnswer(BaseModel):
    """Full user query response including citations and one or more partial answers"""

    answer: List[PartialQAnswer]

    def get_first_citation(self):
        """Return the first citation from any partial answers (utility fn for UI)"""
        for partial in self.answer:
            if partial.citations:
                return partial.citations[0]
        raise ValueError("No citations found in any partial answers")

    def pprint(self) -> str:
        """Format the FullQAnswer to a string for display by a chatbot
        (namely by concatenating partial answers)"""
        result = ""
        citation_counter = 1

        for partial in self.answer:
            result += partial.partial_answer
            for _citation in partial.citations:
                result += f"[{citation_counter}]"
                citation_counter += 1
            result += "\n"
        return result
