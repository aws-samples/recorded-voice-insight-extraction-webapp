# ReVIEW API Documentation

This document provides a comprehensive overview of the ReVIEW application's API, including both REST and WebSocket endpoints.

## REST API

The REST API is fully documented in the OpenAPI specification file: [REST_openAPI_spec.yaml](./REST_openAPI_spec.yaml)

### Available Endpoints

- **POST /llm** - Invoke Bedrock foundation models for text generation
- **POST /ddb** - Interact with DynamoDB for data storage and retrieval
- **POST /s3-presigned** - Generate S3 presigned URLs for file operations
- **POST /kb-job-deletion** - Delete knowledge base jobs and associated files
- **POST /subtitles** - Retrieve and optionally translate subtitles
- **GET/POST/PUT/DELETE /analysis-templates** - Manage analysis templates (CRUD operations)
- **GET/PUT/DELETE /analysis-templates/{template_id}** - Operations on specific templates

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

The WebSocket API provides real-time streaming responses for knowledge base queries and chat functionality.

### Connection
- Connect to the WebSocket endpoint: `wss://api-gateway-url/prod`
- **No authentication required during connection** - authentication is handled in message bodies
- The WebSocket API uses chunked message delivery for large responses

### Authentication
Authentication is handled within each message rather than during connection:
- Include the `username` field in every message
- The backend validates the user's authentication status using Cognito
- Invalid or missing authentication will result in error responses

### Message Format
Send messages in this format:
```json
{
  "action": "$default",
  "messages": "<JSON stringified messages array>",
  "username": "<cognito_username>",
  "media_names": "<JSON stringified array of media names (optional)>",
  "transcript_job_id": "<job_id if querying a single file (optional)>"
}
```

#### Message Fields:
- **action**: Always use `"$default"` for query operations
- **messages**: JSON stringified array of conversation messages in the format:
  ```json
  [{"role": "user", "content": [{"text": "Your question here"}]}]
  ```
- **username**: The Cognito username of the authenticated user
- **media_names**: (Optional) JSON stringified array of media file names to query across multiple files
- **transcript_job_id**: (Optional) UUID of a specific transcript job when querying a single file

### Response Format
Responses are streamed as chunked FullQAnswer objects. Each chunk contains:
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

### Session Management
- WebSocket connections are managed with automatic session cleanup
- Sessions have TTL (time-to-live) for automatic expiration
- Large responses are automatically chunked and reassembled on the client side

## Authentication

### REST API Authentication
All REST endpoints use Amazon Cognito for authentication:
1. Obtain a JWT access token from your Cognito User Pool
2. Include the token in the Authorization header: `Authorization: Bearer <token>`
3. Tokens are validated on each request

### WebSocket API Authentication
WebSocket authentication is handled per-message:
1. No authentication required during WebSocket connection
2. Include your Cognito `username` in each message
3. The backend validates user permissions for each request
4. Invalid authentication results in error responses

## Example Usage

### REST API Example (Python)
```python
import requests
import json

# Assume you have obtained a Cognito JWT token
token = "your_cognito_jwt_token"
api_base_url = "https://your-api-gateway-url"

# Example 1: Query LLM
response = requests.post(
    f"{api_base_url}/llm",
    json={
        "foundation_model_id": "us.amazon.nova-pro-v1:0",
        "system_prompt": "You are a helpful assistant that analyzes transcripts.",
        "main_prompt": "Summarize the key points from this transcript: {transcript}",
        "bedrock_kwargs": {"temperature": 0, "maxTokens": 2000}
    },
    headers={"Authorization": f"Bearer {token}"},
)
result = response.json()
print(result)

# Example 2: Get analysis templates
response = requests.get(
    f"{api_base_url}/analysis-templates",
    headers={"Authorization": f"Bearer {token}"},
)
templates = response.json()
print(templates)

# Example 3: Create new analysis template
response = requests.post(
    f"{api_base_url}/analysis-templates",
    json={
        "template_short_name": "Action Items Extractor",
        "template_description": "Extracts action items and assigns responsibilities",
        "template_prompt": "Extract all action items from this transcript and identify who is responsible: {transcript}",
        "system_prompt": "You are an intelligent assistant who analyzes transcripts.",
        "model_id": "us.amazon.nova-pro-v1:0",
        "bedrock_kwargs": {"temperature": 0.1, "maxTokens": 2000}
    },
    headers={"Authorization": f"Bearer {token}"},
)
new_template = response.json()
print(new_template)

# Example 4: Generate presigned URL for file upload
response = requests.post(
    f"{api_base_url}/s3-presigned",
    json={
        "action": "upload_media_file",
        "username": "your_username",
        "media_file_name": "meeting_recording.mp4"
    },
    headers={"Authorization": f"Bearer {token}"},
)
presigned_data = response.json()
print(presigned_data)
```

### WebSocket API Example (Python)
```python
import websocket
import json
import threading

# WebSocket URL (note: uses 'prod' stage, not 'dev')
ws_url = "wss://your-api-gateway-url/prod"
username = "your_cognito_username"

def on_message(ws, message):
    """Handle incoming WebSocket messages"""
    try:
        response = json.loads(message)
        print("Received response:", response)
        
        # Process the streaming answer
        if "answer" in response:
            for answer_part in response["answer"]:
                partial_answer = answer_part.get("partial_answer", "")
                citations = answer_part.get("citations", [])
                
                print(f"Answer part: {partial_answer}")
                if citations:
                    print(f"Citations: {citations}")
                    
    except json.JSONDecodeError:
        print(f"Received non-JSON message: {message}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")

def on_open(ws):
    print("WebSocket connection opened")
    
    # Example 1: Query across multiple media files
    query_message = {
        "action": "$default",
        "messages": json.dumps([{
            "role": "user", 
            "content": [{"text": "What were the main topics discussed in these meetings?"}]
        }]),
        "username": username,
        "media_names": json.dumps(["meeting1.mp4", "meeting2.mp4"])
    }
    
    ws.send(json.dumps(query_message))

# Create WebSocket connection (no auth headers needed)
ws = websocket.WebSocketApp(
    ws_url,
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

# Run WebSocket in a separate thread
ws_thread = threading.Thread(target=ws.run_forever)
ws_thread.daemon = True
ws_thread.start()

# Keep the main thread alive
try:
    ws_thread.join()
except KeyboardInterrupt:
    print("Closing WebSocket connection...")
    ws.close()
```

### WebSocket API Example (JavaScript/Browser)
```javascript
// WebSocket connection (no auth headers needed)
const ws = new WebSocket('wss://your-api-gateway-url/prod');
const username = 'your_cognito_username';

ws.onopen = function(event) {
    console.log('WebSocket connection opened');
    
    // Send a query
    const queryMessage = {
        action: '$default',
        messages: JSON.stringify([{
            role: 'user',
            content: [{ text: 'Summarize the key points from this meeting.' }]
        }]),
        username: username,
        transcript_job_id: 'your-job-uuid-here'
    };
    
    ws.send(JSON.stringify(queryMessage));
};

ws.onmessage = function(event) {
    try {
        const response = JSON.parse(event.data);
        console.log('Received response:', response);
        
        // Process streaming answer
        if (response.answer) {
            response.answer.forEach(answerPart => {
                const partialAnswer = answerPart.partial_answer || '';
                const citations = answerPart.citations || [];
                
                console.log('Answer part:', partialAnswer);
                if (citations.length > 0) {
                    console.log('Citations:', citations);
                }
            });
        }
    } catch (error) {
        console.error('Error parsing WebSocket message:', error);
    }
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};

ws.onclose = function(event) {
    console.log('WebSocket connection closed');
};
```

## Error Handling

### REST API Errors
REST endpoints return standard HTTP status codes:
- **200**: Success
- **400**: Bad Request (invalid parameters)
- **401**: Unauthorized (invalid or missing token)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found
- **409**: Conflict (resource already exists)
- **500**: Internal Server Error
- **503**: Service Unavailable (throttling)

Error responses follow this format:
```json
{
  "statusCode": 400,
  "body": "Error description"
}
```

### WebSocket API Errors
WebSocket errors are returned as JSON messages:
```json
{
  "error": "Error description",
  "statusCode": 400
}
```

Common WebSocket errors:
- Authentication failures (invalid username)
- Invalid message format
- Missing required fields
- Internal processing errors

## Rate Limiting and Throttling

- REST API endpoints may be subject to API Gateway throttling limits
- WebSocket connections have built-in throttling (500 burst, 1000 steady-state)
- Bedrock model invocations are subject to service quotas
- Large file operations may have extended timeouts

## Best Practices

1. **Authentication**: Always validate tokens before making requests
2. **Error Handling**: Implement proper error handling for all API calls
3. **WebSocket Management**: Handle connection drops and implement reconnection logic
4. **File Uploads**: Use the presigned URL workflow for secure file uploads
5. **Streaming Responses**: Process WebSocket messages incrementally for better UX
6. **Resource Cleanup**: Delete unused jobs and files to manage costs
7. **Template Management**: Use analysis templates for consistent processing workflows
