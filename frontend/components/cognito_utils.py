# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for working with Amazon Cognito"""

from streamlit_cognito_auth import CognitoAuthenticator
import os


def login():
    """Display cognito login screen, on success set "auth_username" session state variable
    (and a bunch of other session variables not explicitly used elsewhere)
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
