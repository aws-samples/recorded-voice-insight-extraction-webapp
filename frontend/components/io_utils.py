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

"""Utilities related to accessing I/O"""

import os
import pandas as pd


def check_valid_file_extension(filename: str) -> bool:
    """Check to make sure files are the acceptable video/audio
    format for transcription"""
    _, extension = os.path.splitext(filename)
    media_format = extension[1:].lower()  # Drop the leading "." in extension
    return media_format in {"mp3", "mp4", "wav", "flac", "ogg", "amr", "webm", "m4a"}


def get_analysis_templates() -> pd.DataFrame:
    """Read analysis templates from csv and return df"""
    dirname = os.path.dirname(__file__)  # Location of this python file
    analysis_templates_file_fullpath = os.path.join(
        dirname, "../assets/analysis_templates.csv"
    )
    return pd.read_csv(analysis_templates_file_fullpath)
