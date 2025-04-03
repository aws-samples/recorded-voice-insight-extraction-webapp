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

"""Utilities related to captions, requiring webvtt dependency"""

from datetime import datetime, timedelta

import webvtt


def time_to_seconds(time_str):
    """
    Convert a time string in format HH:MM:SS.ms (like in webvtt captions) to seconds (float)

    Args:
        time_str (str): Time string in format "HH:MM:SS.ms"

    Returns:
        float: Total seconds
    """
    # Parse the time string
    time_obj = datetime.strptime(time_str, "%H:%M:%S.%f")

    # Calculate total seconds
    delta = timedelta(
        hours=time_obj.hour,
        minutes=time_obj.minute,
        seconds=time_obj.second,
        microseconds=time_obj.microsecond,
    )

    return delta.total_seconds()


def build_timestamped_segmented_transcript(vtt_string: str) -> str:
    """Convert vtt from Amazon Transcribe into a string that
    has integer timestamps easy for the LLM to comprehend

    [1] Hello.\n
    [3] Thanks, for having me.\n
    [10] This is a transcript!\n
    """

    # Convert vtt_string into webvtt object
    vtt = webvtt.from_string(vtt_string)
    return "\n".join(
        [f"[{int(time_to_seconds(caption.start))}] {caption.text}" for caption in vtt]
    )


# def build_timestamped_segmented_transcript(full_transcript_json: dict) -> str:
#     """Convert json transcript from Amazon Transcribe into a string that
#     is segmented into ([integer]) timestamps

#     [1] Hello.\n
#     [3] Thanks, for having me.\n
#     [10] This is a transcript!\n
#     """

#     items = full_transcript_json["results"]["items"]
#     lines = []  # list of strings
#     start_new_line = True
#     for item in items:
#         word = item["alternatives"][0]["content"]

#         if start_new_line:
#             lines.append("")
#             start_new_line = False
#             st = item["start_time"]
#             lines[-1] = f"[{int(float(st))}] {word}"
#         else:
#             if word == ".":
#                 lines[-1] += f"{word}"
#                 start_new_line = True
#             elif item["type"] == "punctuation":
#                 lines[-1] += f"{word}"
#             else:
#                 lines[-1] += f" {word}"
#     return "\n".join(lines)
