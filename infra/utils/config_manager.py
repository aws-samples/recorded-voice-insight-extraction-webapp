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

import yaml
from typing import Dict, Any
import re


class ConfigManager:
    def __init__(self, config_file_path: str):
        self.config: Dict[str, Any] = self._load_config(config_file_path)
        self._validate_config()

    def _validate_config(self):
        # Ensure stack name is not empty
        assert self.config["stack_name_base"] != "", "Stack name cannot be empty"

        # Ensure stack name is only numbers, letters, and hyphens
        assert re.match(
            r"^[a-zA-Z0-9-]+$", self.config["stack_name_base"]
        ), "Stack name must only contain numbers, letters, and/or hyphens"

    def _load_config(self, config_file_path: str) -> Dict[str, Any]:
        with open(config_file_path, "r") as config_file:
            return yaml.safe_load(config_file)

    def get_props(self) -> Dict[str, str]:
        """Map what is in the config file to variable names used by the stacks"""

        unique_stack_name = (
            self.config["stack_name_base"].lower() + "-" + self.config["account_id"]
        )
        s3_bucket_name = (
            f"{unique_stack_name}-{self.config['s3']['bucket_name_suffix']}"
        )
        props = {
            "stack_name_base": self.config["stack_name_base"],
            "unique_stack_name": unique_stack_name,
            "s3_bucket_name": s3_bucket_name,
            "s3_bucket_arn": f"arn:aws:s3:::{s3_bucket_name}",
            "s3_logging_bucket_name": f"{unique_stack_name}-{self.config['s3']['logging_bucket_name_suffix']}",
            "s3_recordings_prefix": self.config["s3"]["recordings_prefix"],
            "s3_transcripts_prefix": self.config["s3"]["transcripts_prefix"],
            "s3_text_transcripts_prefix": self.config["s3"]["text_transcripts_prefix"],
            "ddb_table_name": self.config["dynamo_db"]["table_name"],
            "account_id": self.config["account_id"],
            "region_name": self.config["region_name"],
            "oss_collection_name": self.config["oss"]["collection_name"],
            "oss_index_name": self.config["oss"]["index_name"],
            "embedding_model_id": self.config["embedding"]["model_id"],
            "embedding_model_arn": self.config["embedding"]["model_arn"],
            "kb_chunking_strategy": self.config["kb"]["chunking_strategy"],
            "kb_max_tokens": self.config["kb"]["max_tokens"],
            "kb_overlap_percentage": self.config["kb"]["overlap_percentage"],
            "kb_role_name": f"{unique_stack_name}-kb-role",
            "kb_num_chunks": self.config["kb"]["num_chunks"],
            "llm_model_id": self.config["llm"]["model_id"],
            "llm_model_arn": self.config["llm"]["model_arn"],
            "cognito_pool_name": self.config["frontend"]["cognito_pool_name"],
        }

        return props


# Usage example:
if __name__ == "__main__":
    config_manager = ConfigManager("config.yaml")
    props = config_manager.get_props()
    print(props)