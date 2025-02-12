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


import boto3
import logging

# Initialize Cognito client
cognito = boto3.client("cognito-idp")

logger = logging.getLogger()
logger.setLevel("DEBUG")


def lambda_handler(event, context):
    logger.debug(f"{event=}")
    # Extract the bearer token from the Authorization header
    try:
        # Request should have a header naemd Authorization with a value
        # like "Bearer blahblahblah"
        token = event["headers"]["Authorization"].split(" ")[1]
    except (KeyError, IndexError) as e:
        logger.debug(f"Access denied due to request header error: {str(e)}")
        return generate_policy("user", "Deny", event["methodArn"])

    try:
        # Verify the token with Cognito
        response = cognito.get_user(AccessToken=token)

        # If we reach here, the token is valid
        user_id = response["Username"]
        return generate_policy(user_id, "Allow", event["methodArn"])

    except cognito.exceptions.NotAuthorizedException as e:
        # Token is invalid or expired
        logger.debug(f"Access denied due to invalid token: Exception = {str(e)}")
        return generate_policy("user", "Deny", event["methodArn"])

    except Exception as e:
        logger.degbug(f"Unknown error: {str(e)}")
        return generate_policy("user", "Deny", event["methodArn"])


def generate_policy(principal_id, effect, resource):
    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {"Action": "execute-api:Invoke", "Effect": effect, "Resource": resource}
            ],
        },
    }
