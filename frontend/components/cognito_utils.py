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

"""Helper utilities for working with Amazon Cognito"""

import streamlit as st
from streamlit_cognito_auth import CognitoAuthenticator
import os


def login():
    """Display cognito login screen, on success set "auth_username" session state variable
    and "auth_id_token", and a bunch of other session variables not explicitly used elsewhere.
    """

    # This sets "auth_username" session state variable if successful, otherwise it's ""
    authenticator = CognitoAuthenticator(
        **get_cognito_secrets(),
        use_cookies=False,  # TODO: figure out how to get True working properly
    )

    authenticator.login()


def logout():
    """Log out"""
    authenticator = CognitoAuthenticator(
        **get_cognito_secrets(),
        use_cookies=False,  # TODO: figure out how to get True working properly
    )

    authenticator.logout()


def get_cognito_secrets():
    """Get cognito secrets from environment and return kwargs for authenticator"""

    return {
        "pool_id": os.environ["COGNITO_POOL_ID"],
        "app_client_id": os.environ["COGNITO_CLIENT_ID"],
    }
