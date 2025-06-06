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

"""Lambda to handle interactions with Bedrock foundation models"""

from bedrock.bedrock_utils import LLM
import logging
import json

# Class to handle connections to Bedrock foundation models
llm = LLM()

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
    """
    Event will provide:
    * foundation model ID (str)
    * system_prompt (str)
    * main_prompt (str)
    * bedrock keyword args (dict)

    Lambda returns a string generated by LLM
    """
    # When this lambda is called by the frontend via API gateway, the event
    # has a 'body' key. When this lambda is called by other lambdas, this is
    # unnecessary

    logger.debug(f"{event=}")

    if "body" in event:
        event = json.loads(event["body"])

    foundation_model_id = event["foundation_model_id"]
    system_prompt = event["system_prompt"]
    main_prompt = event["main_prompt"]
    bedrock_kwargs = event["bedrock_kwargs"]

    # Inference LLM & return result
    try:
        generation = llm.generate(
            model_id=foundation_model_id,
            system_prompt=system_prompt,
            prompt=main_prompt,
            kwargs=bedrock_kwargs,
        )
    except Exception as e:
        return {"statusCode": 500, "body": f"Internal server error: {e}"}

    return {"statusCode": 200, "body": json.dumps(generation)}
