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
import copy
import logging
import webvtt
import boto3
from lambda_utils.vtt_utils import time_to_seconds
from botocore.config import Config

logger = logging.getLogger(__name__)

config = Config(retries={"total_max_attempts": 3, "mode": "standard"})
bedrock_client = boto3.client("bedrock-runtime", config=config)


TRANSLATION_PROMPT = """\
Here are captions from a video, presented line by line.

# Captions:
{ORIGINAL_VTT_CAPTIONS}

# Instructions:
Your task is to translate these captions from the original language to {NEW_LANGUAGE}. 
You MUST preserve the line-by-line structure and original timestamps.
Read through these captions line by line, and for each line, translate it to {NEW_LANGUAGE} before proceeding to the next line. 
The number of lines in the original captions MUST equal the number of lines in the translated captions.

"""


def translate_vtt(
    foundation_model_id: str,
    vtt_string: str,
    target_language: str,
    start_time_seconds: float = 0,
    end_time_seconds: float = float("inf"),
) -> str:
    """
    Convert vtt string into new vtt string in new language.
    If start_time and end_time are provided, only the lines between those times are translated,
    the rest are left in the original source language
    """

    # Convert vtt string into vtt object
    vtt_object = webvtt.from_string(vtt_string)

    # line_by_line_captions looks like:
    # 1 this is the first line
    # 2 and this is the second
    # 3 line blah blah

    translated_line_indices = set()
    # Translate only lines after start_time, before end_time
    line_by_line_captions = []
    for i, caption in enumerate(vtt_object):
        if (
            time_to_seconds(caption.start) >= start_time_seconds
            and time_to_seconds(caption.start) <= end_time_seconds
        ):
            line_by_line_captions.append(f"{i} {caption.text}")
            translated_line_indices.add(i)
    line_by_line_captions = "\n".join(line_by_line_captions)

    SYSTEM_PROMPT_CONTENT = f"You are an AI which translates captions into {target_language} in a line-by-line fashion."
    USER_MESSAGE_CONTENT = TRANSLATION_PROMPT.format(
        ORIGINAL_VTT_CAPTIONS=line_by_line_captions, NEW_LANGUAGE=target_language
    )
    AI_PREFILL_CONTENT = "# Translated captions:\n\n"

    converse_kwargs = {
        "system": [{"text": SYSTEM_PROMPT_CONTENT}],
        "modelId": foundation_model_id,
        # Full messages list, minus the latest user message, replaced by the full prompt
        "messages": [
            {"role": "user", "content": [{"text": USER_MESSAGE_CONTENT}]},
            {"role": "assistant", "content": [{"text": AI_PREFILL_CONTENT}]},
        ],
        "inferenceConfig": {
            "temperature": 0,
            "maxTokens": 2000,
        },
    }
    llm_response = bedrock_client.converse(**converse_kwargs)
    translated_vtt_string = llm_response["output"]["message"]["content"][0]["text"]
    logger.debug(f"LLM generated vtt string translated: {translated_vtt_string}")
    # Create a dict of line_index : translated_caption
    translated_lines = {}
    for translated_line in translated_vtt_string.split("\n"):
        try:
            line_idx = int(translated_line.split(" ")[0])
            translated_lines[line_idx] = " ".join(translated_line.split(" ")[1:])
        except Exception:
            continue

    # Checks to make sure the LLM translated every line it was provided with
    if not translated_line_indices and len(vtt_object) != len(translated_lines):
        logger.warning(
            f"Warning, line by line translation issue. {len(vtt_object)=}, {len(translated_lines)=}"
        )
    if translated_line_indices and len(line_by_line_captions.split("\n")) != len(
        translated_lines
    ):
        logger.warning(
            f"Warning, line by line translation issue. {len(translated_line_indices)=}, {len(translated_lines)=}"
        )

    # Create an output vtt object with the translated lines replaced.
    # Non-transltaed lines stay in the source language.
    translated_vtt_object = copy.deepcopy(vtt_object)
    for i, translated_line in translated_lines.items():
        translated_vtt_object[i].text = translated_line

    logger.debug("Full translated VTT: {translated_vtt_object.content}")
    # Return vtt object dumped to string
    return translated_vtt_object.content
