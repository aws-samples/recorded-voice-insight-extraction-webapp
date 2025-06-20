# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
from typing import Any, Dict, Optional


class CORSResponse:
    """Utility class for creating Lambda responses with proper CORS headers."""
    
    @staticmethod
    def get_cors_headers() -> Dict[str, str]:
        """Get standard CORS headers for API Gateway responses."""
        return {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Content-Type': 'application/json'
        }
    
    @staticmethod
    def success_response(body: Any, status_code: int = 200) -> Dict[str, Any]:
        """Create a successful response with CORS headers."""
        return {
            'statusCode': status_code,
            'headers': CORSResponse.get_cors_headers(),
            'body': json.dumps(body)
        }
    
    @staticmethod
    def error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
        """Create an error response with CORS headers."""
        return {
            'statusCode': status_code,
            'headers': CORSResponse.get_cors_headers(),
            'body': json.dumps({'error': message})
        }
