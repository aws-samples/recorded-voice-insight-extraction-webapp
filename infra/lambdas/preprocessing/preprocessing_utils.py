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


import os


def extract_username_from_s3_URI(uri: str) -> str:
    """URIs are like s3://bucket/blah/username/file_they_uploaded.mp4
    Return username
    TODO: test for security flaws, e.g. if usernames can contain / character"""
    return os.path.split(uri)[0].split("/")[-1]


def extract_uuid_from_s3_URI(uri: str) -> str:
    """URIs are like s3://bucket/blah/username/[uuid].txt.metadata.json
    Return uuid"""
    return os.path.split(uri)[-1].split(".")[0]


def build_kb_metadata_json(username: str, media_name: str) -> dict:
    """Custom metadata for bedrock knowledge base to grab and include in OpenSearch for filtering"""
    return {"metadataAttributes": {"username": username, "media_name": media_name}}


def build_simplified_bda_video_string(bda_output: dict) -> str:
    """Given bda_output dict (from Bedrock Data Automation)
    for a video file, convert the dict to a simplified string, dropping
    unnecessary information (like transcript, which is extracted separately)

    The output will look like this (with xxx's filled in):

    Chapter 1:
        - Start time (seconds) = xxx (rounded down to int)
        - Summary = xxx
        - Tags = xxx (from this chapter's ["iab_categories"][i]["category"])
        - Text extracted from video frames with timestamps in seconds =
            - [xxx]: xxx (string of this chapter's ["frames"]["text_words"][i]["text"] concatenated with spaces, timestamp is ["frames"][i]["timestamp_millis] converted to int seconds)

    Chapter 2: ....


    Args:
        bda_output (dict): The Bedrock Data Automation output dictionary

    Returns:
        str: simplified bda output as a string for imputing into an LLM context window later
    """
    # Check if this is a video file
    if bda_output.get("metadata", {}).get("semantic_modality") != "VIDEO":
        return ""

    result = []

    # Process each chapter
    for i, chapter in enumerate(bda_output.get("chapters", [])):
        chapter_text = [f"Chapter {i + 1}:"]

        # Start time in seconds
        start_time_ms = chapter.get("start_timestamp_millis", 0)
        start_time_sec = int(start_time_ms / 1000)
        chapter_text.append(f"    - Start time (seconds) = [{start_time_sec}]")

        # Summary
        summary = chapter.get("summary", "")
        chapter_text.append(f"    - Summary = {summary}")

        # Tags from IAB categories
        tags = []
        for category_item in chapter.get("iab_categories", []):
            category = category_item.get("category", "")
            if category:
                tags.append(category)

        tags_str = ", ".join(tags) if tags else "None"
        chapter_text.append(f"    - Tags = {tags_str}")

        # Text extracted from video frames
        chapter_text.append(
            "    - Text extracted from video frames with timestamps in seconds ="
        )

        frames = chapter.get("frames", [])
        if frames:
            # Track seen text to avoid duplicates
            seen_texts = set()

            for frame in frames:
                timestamp_ms = frame.get("timestamp_millis", 0)
                timestamp_sec = int(timestamp_ms / 1000)

                # Concatenate all text words from this frame
                text_words = []
                for word_obj in frame.get("text_words", []):
                    word = word_obj.get("text", "")
                    if word:
                        text_words.append(word)

                frame_text = " ".join(text_words)
                # Only include this text if we haven't seen it before in this chapter
                if frame_text and frame_text not in seen_texts:
                    chapter_text.append(f"        - [{timestamp_sec}]: {frame_text}")
                    seen_texts.add(frame_text)
        else:
            chapter_text.append("        - No text extracted from frames")

        result.append("\n".join(chapter_text))

    # Add overall video summary if available
    video_summary = bda_output.get("video", {}).get("summary", "")
    if video_summary:
        result.append(f"\nOverall Video Summary:\n{video_summary}")

    return "\n\n".join(result)
