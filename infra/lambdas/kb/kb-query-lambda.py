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

import os
from boto3 import client
import json

bedrock_agent_runtime_client = client(
    "bedrock-agent-runtime", region_name=os.environ["AWS_REGION"]
)

# TODO: use retrieve API with custom stuff to handle chunks and metadata
CHAT_PROMPT_TEMPLATE = """
You are an intelligent AI which attempts to answer questions based on an automatically generated transcript.

<transcript>$search_results</transcript>

Each line in the transcript above includes an integer timestamp (in seconds) within square brackets, followed by a statement.

Using only information in the above transcript, attempt to answer the question below.

<question>$query</question>

Your response must contain two parts, an integer timestamp representing the start of the portion of the transcript which contains the answer to the question, and an answer to the question itself. The timestamp should be included within <timestamp></timestamp> tags, and the answer within <answer></answer> tags. If you are unable to answer the question, return a timestamp of -1 and an answer of "I am unable to find the answer to your question within the provided transcript."
"""


def lambda_handler(event, context):
    question = json.loads(event["body"])["question"]

    input_data = {
        "input": {"text": question},
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": os.environ["KNOWLEDGE_BASE_ID"],
                "modelArn": os.environ["LLM_ARN"],
            },
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "numberOfResults": 1,
                    # "filter": retrieval_filter, #TODO: filter based on user ID
                },
            },
            "generationConfiguration": {
                "promptTemplate": {"textPromptTemplate": CHAT_PROMPT_TEMPLATE}
            },
        },
    }

    command = bedrock_agent_runtime_client.RetrieveAndGenerateCommand(input_data)
    response = bedrock_agent_runtime_client.send(command)

    return {"response": response.output.text}
