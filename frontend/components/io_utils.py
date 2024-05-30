"""Utilities related to accessing I/O"""

import os


def check_valid_file_extension(filename: str) -> bool:
    """Check to make sure files are the acceptable video/audio
    format for transcription"""
    _, extension = os.path.splitext(filename)
    media_format = extension[1:].lower()  # Drop the leading "." in extension
    return media_format in {"mp3", "mp4", "wav", "flac", "ogg", "amr", "webm", "m4a"}
