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


def bda_output_to_vtt(bda_output: dict) -> str:
    """Given bda_output dict (from Bedrock Data Automation)
    for either a video or audio file, create a webvtt object and
    return its string representation.
    Each line in the vtt represents one "audio_segments" in the BDA output.

    Args:
        bda_output (dict): The Bedrock Data Automation output dictionary

    Returns:
        str: WebVTT formatted string representation
    """
    from webvtt import WebVTT, Caption

    vtt = WebVTT()

    # Determine if we're dealing with video or audio
    modality = bda_output.get("metadata", {}).get("semantic_modality", "")

    # Get the audio segments based on file type
    segments = []
    if modality == "VIDEO":
        # For video files, audio_segments are within chapters
        for chapter in bda_output.get("chapters", []):
            segments.extend(chapter.get("audio_segments", []))
    elif modality == "AUDIO":
        # For audio files, audio_segments are at the top level
        segments = bda_output.get("audio_segments", [])

    # Process each segment
    for i, segment in enumerate(segments):
        if segment.get("type") == "TRANSCRIPT":
            # Convert milliseconds to WebVTT format (HH:MM:SS.mmm)
            start_ms = segment.get("start_timestamp_millis", 0)
            end_ms = segment.get("end_timestamp_millis", 0)

            # Convert milliseconds to HH:MM:SS.mmm format
            start_time = ms_to_vtt_time(start_ms)
            end_time = ms_to_vtt_time(end_ms)

            # Create caption with text
            caption = Caption(start_time, end_time, segment.get("text", ""))

            # Add an identifier (optional)
            caption.identifier = f"{i + 1}"

            # Add caption to WebVTT object
            vtt.captions.append(caption)

    # Return WebVTT object converted to string
    return vtt.content


def ms_to_vtt_time(milliseconds: int) -> str:
    """Convert milliseconds to WebVTT time format (HH:MM:SS.mmm)

    Args:
        milliseconds (int): Time in milliseconds

    Returns:
        str: Time in WebVTT format (HH:MM:SS.mmm)
    """
    # Handle edge case
    if milliseconds < 0:
        milliseconds = 0

    # Calculate hours, minutes, seconds, and remaining milliseconds
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)

    # Format as HH:MM:SS.mmm
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
