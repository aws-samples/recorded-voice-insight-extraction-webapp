# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for working with Amazon Bedrock"""


def build_timestamped_segmented_transcript(full_transcript_json: dict) -> str:
    """Convert json transcript from Amazon Transcribe into a string that
    is segmented into ([integer]) timestamps

    [1] Hello.\n
    [3] Thanks, for having me.\n
    [10] This is a transcript!\n
    """

    items = full_transcript_json["results"]["items"]
    lines = []  # list of strings
    start_new_line = True
    for item in items:
        word = item["alternatives"][0]["content"]

        if start_new_line:
            lines.append("")
            start_new_line = False
            st = item["start_time"]
            lines[-1] = f"[{int(float(st))}] {word}"
        else:
            if word == ".":
                lines[-1] += f"{word}"
                start_new_line = True
            elif item["type"] == "punctuation":
                lines[-1] += f"{word}"
            else:
                lines[-1] += f" {word}"
    return "\n".join(lines)
