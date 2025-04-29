# ReVIEW API Documentation

This document provides a comprehensive overview of the ReVIEW application's API, including both REST and WebSocket endpoints.

## REST API

The REST API is fully documented in the OpenAPI specification file: [REST_openAPI_spec.yaml](./REST_openAPI_spec.yaml)

### Using the OpenAPI Specification

You can use the OpenAPI specification file with various tools to explore and test the API:

#### Option 1: Swagger Editor (Online)
1. Visit [Swagger Editor](https://editor.swagger.io/)
2. Click on "File" > "Import File" and upload the `REST_openAPI_spec.yaml` file
3. The editor will render the API documentation with interactive UI elements
4. You can test endpoints directly from the interface (note: you'll need to provide your own authentication token)

#### Option 2: Swagger UI (Self-hosted)
1. Clone the [Swagger UI repository](https://github.com/swagger-api/swagger-ui)
2. Follow their setup instructions to host it locally
3. Point it to your `REST_openAPI_spec.yaml` file

#### Option 3: Postman
1. Open Postman
2. Click "Import" > "File" and select the `REST_openAPI_spec.yaml` file
3. Postman will create a collection with all the API endpoints
4. You can then add your authentication token and test the endpoints

#### Option 4: AWS API Gateway Console
If you have access to the AWS console where the API is deployed:
1. Navigate to API Gateway
2. Select your API
3. Click on "Documentation" in the left panel
4. You can import the OpenAPI specification here for reference

## WebSocket API

The WebSocket API is not fully representable in OpenAPI 3.0, but here's how to connect and use it:

### Connection
- Connect to the WebSocket endpoint with a valid Cognito access token in the Authorization header
- URL format: `wss://api-gateway-url/dev`

### Message Format
Send messages in this format:
```json
{
  "action": "$default",
  "messages": "<JSON stringified messages array>",
  "username": "<username>",
  "media_names": "<JSON stringified array of media names>",
  "transcript_job_id": "<job_id if querying a single file>"
}
```

### Response Format
Responses are streamed as FullQAnswer objects:
```json
{
  "answer": [
    {
      "partial_answer": "This is part of the answer",
      "citations": [
        {
          "media_name": "example.mp4",
          "timestamp": 123
        }
      ]
    }
  ]
}
```

## Authentication

Both APIs use Amazon Cognito for authentication:
1. Obtain a JWT token from Cognito User Pool
2. Include the token in the Authorization header as a Bearer token
3. For REST API: `Authorization: Bearer <token>`
4. For WebSocket API: Include the same header during connection

## Example Usage

### REST API Example (Python)
```python
import requests

# Authenticate with Cognito and get token
# ...

# Make a request to the LLM endpoint
response = requests.post(
    "https://api-gateway-url/llm",
    json={
        "foundation_model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "system_prompt": "You are a helpful assistant",
        "main_prompt": "Tell me about AWS",
        "bedrock_kwargs": {"temperature": 0, "maxTokens": 2000}
    },
    headers={"Authorization": f"Bearer {token}"},
)
result = response.json()
```

### WebSocket API Example (Python)
```python
import websocket
import json

# Authenticate with Cognito and get token
# ...

# Connect to WebSocket API
ws = websocket.create_connection(
    url="wss://api-gateway-url/dev",
    header={"Authorization": f"Bearer {token}"}
)

# Send a query
ws.send(json.dumps({
    "action": "$default",
    "messages": json.dumps([{"role": "user", "content": [{"text": "What was discussed in the meeting?"}]}]),
    "username": "example_user",
    "media_names": json.dumps(["meeting_recording.mp4"])
}))

# Receive streaming responses
while True:
    response = ws.recv()
    if not response:
        break
    parsed_response = json.loads(response)
    # Process the response
    print(parsed_response)

ws.close()
```
