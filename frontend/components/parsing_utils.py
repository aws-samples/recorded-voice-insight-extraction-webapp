# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for parsing LLM responses"""

import re


def extract_timestamp_and_answer(input_string: str) -> tuple[str, int]:
    """
    Extract timestamp and answer strings from LLM response
    and return (answer_string, media_timestamp_in_seconds)
    """
    pattern = re.compile(r"<timestamp>(.*?)</timestamp>", re.DOTALL)
    match = pattern.search(input_string.replace("[", "").replace("]", ""))
    timestamp_int = int(match.group(1))

    pattern = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
    match = pattern.search(input_string)
    answer_str = match.group(1)

    return (answer_str, timestamp_int)
