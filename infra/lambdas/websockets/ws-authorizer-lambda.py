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
logger.setLevel("INFO")


def lambda_handler(event, context):
    logger.info(f"WebSocket authorizer event: {event}")
    
    # Extract the bearer token from either Authorization header or query parameters
    # This supports both the original Streamlit implementation (headers) and new React implementation (query params)
    token = None
    
    try:
        # First try to get token from Authorization header (backward compatibility for Streamlit)
        if "headers" in event and "Authorization" in event["headers"]:
            # Request should have a header named Authorization with a value
            # like "Bearer blahblahblah"
            auth_header = event["headers"]["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                logger.info("Token extracted from Authorization header")
    except (KeyError, IndexError) as e:
        logger.info(f"Could not extract token from Authorization header: {str(e)}")
    
    # If no token from header, try query parameters (for React frontend browser WebSocket compatibility)
    if not token:
        try:
            if "queryStringParameters" in event and event["queryStringParameters"]:
                query_params = event["queryStringParameters"]
                logger.info(f"Query parameters: {query_params}")
                if "authorization" in query_params:
                    # Query param should contain the full bearer token (without "Bearer " prefix)
                    token = query_params["authorization"]
                    # Remove "Bearer " prefix if present in query param
                    if token.startswith("Bearer "):
                        token = token.split(" ")[1]
                    logger.info("Token extracted from query parameters")
        except (KeyError, TypeError) as e:
            logger.info(f"Could not extract token from query parameters: {str(e)}")
    
    # If no token found in either location, deny access
    if not token:
        logger.info("Access denied: No valid token found in headers or query parameters")
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
        logger.debug(f"Unknown error: {str(e)}")
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
