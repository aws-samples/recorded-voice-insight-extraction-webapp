# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for working with Amazon Cognito"""

from streamlit_cognito_auth import CognitoAuthenticator
import boto3
from botocore.exceptions import ClientError
import json


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
    """Get cognito secrets from AWS Secrets Manager and return kwargs for authenticator"""

    # TODO: set these as environment variables on app startup in streamlit container, so as not
    # to be constantly re-retrieving them from secrets
    secret_name = "review-app-cognito-secrets"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret_string = get_secret_value_response["SecretString"]
        secret_json = json.loads(secret_string)
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    return {
        "pool_id": secret_json["cognito-pool-id"],
        "app_client_id": secret_json["cognito-client-id"],
    }
