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


import json


def invoke_lambda(lambda_client, lambda_function_name: str, action: str, params: dict):
    """Generic function to use a boto3 lambda client to invoke a lambda function
    Note: params must be json serializable"""
    lambda_params = {
        "FunctionName": lambda_function_name,
        "InvocationType": "RequestResponse",
        "Payload": json.dumps({"action": action, **params}),
    }

    try:
        response = lambda_client.invoke(**lambda_params)
        result = json.loads(response["Payload"].read().decode("utf-8"))
        
        # Handle both old format and new CORS format
        if result.get("body"):
            # New CORS format - body is already JSON encoded
            try:
                return json.loads(result["body"])
            except (json.JSONDecodeError, TypeError):
                # If body is already parsed or not valid JSON, return as-is
                return result["body"]
        else:
            # Old format - return the result directly
            return result
            
    except Exception as e:
        print(f"Error invoking Lambda: {str(e)}")
        raise
