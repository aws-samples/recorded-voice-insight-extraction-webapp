# ReVIEW React Frontend

This React frontend follows the AWS best practice architecture where:

1. **CloudFront** serves static files only (no API proxying)
2. **React App** makes direct HTTPS calls to API Gateway
3. **API Gateway** handles CORS and authentication

## Architecture Changes

### Before (Broken)
- CloudFront tried to proxy `/api/*` requests to API Gateway
- Complex CloudFront behaviors and path rewriting
- CORS and authentication issues

### After (Working)
- CloudFront only serves static React app from S3
- React app calls API Gateway directly using full URLs
- Simplified configuration and better reliability

## Configuration

The app loads configuration from `/aws-exports.json` which is generated during CDK deployment:

```json
{
  "Auth": {
    "Cognito": {
      "userPoolClientId": "your-client-id",
      "userPoolId": "your-pool-id"
    }
  },
  "API": {
    "REST": {
      "endpoint": "https://api-id.execute-api.region.amazonaws.com/prod"
    }
  },
  "WebSocket": {
    "endpoint": "wss://ws-id.execute-api.region.amazonaws.com/prod"
  }
}
```

## API Client

The new API client (`src/hooks/useHttp.ts`) automatically:
- Loads API endpoint from configuration
- Adds JWT tokens to requests
- Handles authentication errors

## Usage Example

```typescript
import { useAnalysisApi } from '../hooks/useAnalysisApi';

const MyComponent = () => {
  const { loading, error, retrieveAllItems } = useAnalysisApi();
  
  const fetchData = async () => {
    try {
      const jobs = await retrieveAllItems(username, 100);
      // Handle success
    } catch (err) {
      // Error is automatically handled by the hook
    }
  };
  
  return (
    <div>
      {loading && <p>Loading...</p>}
      {error && <p>Error: {error}</p>}
      {/* Your component content */}
    </div>
  );
};
```

## Local Development

For local development, create `public/aws-exports.json` with your API endpoints:

```bash
cp public/aws-exports.json.template public/aws-exports.json
# Edit the file with your actual API Gateway URLs
```

## Dependencies

Key dependencies added:
- `axios`: HTTP client for API calls
- Authentication handled by existing `aws-amplify`

## Benefits

1. **Simpler Configuration**: No complex CloudFront behaviors
2. **Better Performance**: Direct API calls without CloudFront overhead
3. **Easier CORS Management**: Handled at API Gateway level
4. **More Reliable**: Eliminates CloudFront forwarding issues
5. **AWS Best Practice**: Follows reference architecture patterns
