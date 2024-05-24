# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for working with Amazon Cognito"""

from streamlit_cognito_auth import CognitoAuthenticator


def login():
    """Display cognito login screen, on success set "auth_username" session state variable
    (and a bunch of other session variables not explicitly used elsewhere)
    """
    # I made a pool in the console, with advanced app client settings
    POOL_ID = "us-east-1_IC9QGM2xy"
    # I made a test client in the console, client id under "my pool/App integration"
    CLIENT_ID = "5v86tr4kr974bjvejnt27btvsr"
    # I also made a user, kaleko@amazon.com with password adminadmin

    authenticator = CognitoAuthenticator(
        pool_id=POOL_ID,
        app_client_id=CLIENT_ID,
        use_cookies=False,
    )

    # This sets "auth_username" session state variable if successful, otherwise it's ""
    authenticator.login()
