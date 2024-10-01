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


import logging
import os


from oss_client_utils import (
    get_oss_http_client,
    get_session,
)
from oss_utils import (
    MODEL_ID_TO_INDEX_REQUEST_MAP,
    create_index_with_retries,
    get_host_from_collection_endpoint,
)

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
    logger.debug("oss-create-index lambda handler called.")
    logger.debug(f"{event=}")
    logger.debug(f"{context=}")

    props = event["ResourceProperties"]
    logger.info("Create new OpenSearch index with props %s" % props)
    region = os.environ["AWS_REGION"]
    # policy_name = props["data_access_policy_name"]
    collection_endpoint = props["collection_endpoint"]
    host = get_host_from_collection_endpoint(collection_endpoint)
    index_name = props["index_name"]
    embedding_model_id = props["embedding_model_id"]
    index_request = MODEL_ID_TO_INDEX_REQUEST_MAP[embedding_model_id]

    session = get_session()
    # sts_client = get_sts_client(session, region)
    # oss_client = get_oss_client(session, region)
    oss_http_client = get_oss_http_client(session, region, host)

    # update_access_policy_with_caller_arn_if_applicable(
    #     sts_client, oss_client, policy_name
    # )

    logger.info("Creating index {}".format(index_name))
    create_index_with_retries(oss_http_client, index_name, index_request)

    return {"PhysicalResourceId": index_name}
