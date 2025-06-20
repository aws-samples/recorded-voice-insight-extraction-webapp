# ReVIEW React Frontend

This is the React frontend for the Recorded Voice Insight Extraction Webapp (ReVIEW). It provides a modern, responsive user interface for uploading media files, transcribing them, and using AI to analyze and chat with the content.

## Architecture Overview

The frontend follows AWS best practices with a clean separation of concerns:

1. **CloudFront** serves static files (React app, assets, configuration)
2. **React App** makes direct HTTPS calls to API Gateway endpoints
3. **API Gateway** handles CORS, authentication, and routing to backend services
4. **WebSocket API** provides real-time streaming for chat functionality

## Key Features

### Pages
- **File Upload**: Upload audio/video files for transcription and analysis
- **File Management**: View and manage uploaded media files and their processing status
- **Job Status**: Monitor transcription and processing job statuses
- **Chat with Media**: Interactive AI chat with uploaded media files, including:
  - Multi-file selection for cross-media queries
  - Real-time streaming responses
  - Citation buttons that jump to specific timestamps in videos
  - Subtitle support with translation capabilities
- **Analyze Media**: Run custom analysis templates on transcribed media
- **Dashboard**: Overview and navigation hub

### Core Components
- **MediaPlayer**: Video/audio player with subtitle support and timestamp navigation
- **ChatContainer**: Real-time chat interface with streaming responses
- **JobStatusTable**: Real-time job monitoring with status updates
- **MarkdownWithCitations**: Renders AI responses with clickable citations
- **FileUploadComponent**: Drag-and-drop file upload with progress tracking

## Configuration

The app loads configuration dynamically from `/aws-exports.json`, which is generated during CDK deployment:

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

This configuration is automatically populated by the CDK deployment process with the actual resource IDs and endpoints.

## Authentication

The app uses Amazon Cognito for authentication:
- **Login Flow**: Users authenticate through Cognito User Pools
- **Token Management**: AWS Amplify handles JWT token lifecycle automatically
- **API Authorization**: HTTP client automatically adds Bearer tokens to all API requests
- **Session Management**: Tokens are refreshed automatically when needed

## API Integration

### HTTP Client (`src/hooks/useHttp.ts`)
The custom HTTP client provides:
- **Automatic Configuration**: Loads API endpoints from aws-exports.json
- **Authentication**: Automatically adds JWT tokens to requests
- **Error Handling**: Centralized error processing and retry logic
- **Type Safety**: Full TypeScript support for request/response types

### API Modules
- **`analysis.ts`**: Media analysis and template management
- **`database.ts`**: DynamoDB operations for job tracking
- **`fileManagement.ts`**: File operations and metadata management
- **`s3.ts`**: S3 presigned URL generation for secure file uploads
- **`subtitles.ts`**: Subtitle generation and translation services
- **`upload.ts`**: File upload orchestration
- **`websocket.ts`**: Real-time chat functionality with streaming responses

### WebSocket Integration
Real-time chat functionality uses API Gateway WebSocket API:
- **Connection Management**: Automatic connection/reconnection handling
- **Message Streaming**: Chunked response streaming for large AI responses
- **Citation Processing**: Real-time citation extraction and timestamp mapping
- **Error Recovery**: Automatic retry and fallback mechanisms

## Technology Stack

### Core Dependencies
- **React 18**: Modern React with hooks and concurrent features
- **TypeScript**: Full type safety throughout the application
- **Vite**: Fast build tool and development server
- **AWS Amplify**: Authentication and AWS service integration
- **Axios**: HTTP client for API communication

### UI Framework
- **AWS Cloudscape Design System**: Consistent AWS-native UI components
- **React Router**: Client-side routing and navigation
- **React Markdown**: Markdown rendering for AI responses

### Development Tools
- **ESLint**: Code linting and style enforcement
- **Prettier**: Code formatting
- **PostCSS**: CSS processing and optimization
- **Sass**: Enhanced CSS with variables and mixins

## Local Development

### Prerequisites
- Node.js 18+ and npm
- Access to deployed AWS resources (for API endpoints)

### Setup
```bash
cd frontend-react
npm install
npm run dev
```

### Environment Configuration
For local development, you can set environment variables:
```bash
export VITE_WS_API_URL=wss://your-websocket-api-id.execute-api.region.amazonaws.com/prod
```

Note: The production app uses aws-exports.json instead of environment variables.

### Available Scripts
- `npm run dev`: Start development server with hot reload
- `npm run build`: Build production bundle
- `npm run preview`: Preview production build locally
- `npm run lint`: Run ESLint code analysis
- `npm run format`: Format code with Prettier

## Deployment

The frontend is deployed automatically via CDK:

1. **Build Process**: CDK uses Docker to build the React app in a consistent environment
2. **Asset Generation**: Creates optimized production bundle with code splitting
3. **Configuration Injection**: Generates aws-exports.json with actual AWS resource IDs
4. **S3 Deployment**: Uploads built assets and configuration to S3 bucket
5. **CloudFront Distribution**: Serves content globally with caching and compression

### Build Configuration
The CDK deployment process:
```python
# Build React app in Docker container
react_asset = s3deploy.Source.asset(
    app_path,
    bundling=BundlingOptions(
        image=DockerImage.from_registry("public.ecr.aws/sam/build-nodejs18.x:latest"),
        command=["sh", "-c", " && ".join([
            "npm --cache /tmp/.npm install",
            "npm --cache /tmp/.npm run build",
            "cp -aur /asset-input/dist/* /asset-output/",
        ])],
    ),
)

# Generate configuration file
exports_asset = s3deploy.Source.json_data("aws-exports.json", exports_config)

# Deploy both assets
s3deploy.BucketDeployment(
    sources=[react_asset, exports_asset],
    destination_bucket=website_bucket,
    distribution=cloudfront_distribution,
)
```

## Security Considerations

- **Authentication**: All API calls require valid Cognito JWT tokens
- **CORS**: Properly configured at API Gateway level
- **Content Security**: CloudFront serves static content with appropriate headers
- **Token Security**: JWT tokens are stored securely by AWS Amplify
- **API Security**: No sensitive data exposed in client-side code

## Performance Optimizations

- **Code Splitting**: Vite automatically splits code for optimal loading
- **Tree Shaking**: Unused code is eliminated from production bundles
- **Asset Optimization**: Images and other assets are optimized during build
- **CloudFront Caching**: Global CDN with intelligent caching strategies
- **Lazy Loading**: Components and routes are loaded on demand

## Troubleshooting

### Common Issues

1. **WebSocket Connection Errors**: Ensure aws-exports.json is accessible and contains valid WebSocket endpoint
2. **Authentication Failures**: Check Cognito configuration and user pool settings
3. **API Errors**: Verify API Gateway endpoints are accessible and CORS is configured
4. **Build Failures**: Ensure all dependencies are installed and TypeScript types are correct

### Debug Mode
Enable debug logging by setting localStorage:
```javascript
localStorage.setItem('debug', 'true');
```

### Network Issues
Check browser developer tools Network tab for:
- Failed API requests
- CORS errors
- Authentication token issues
- WebSocket connection problems

## Contributing

When making changes to the frontend:

1. Follow TypeScript best practices and maintain type safety
2. Use AWS Cloudscape components for consistency
3. Add proper error handling for all API calls
4. Update types when modifying API interfaces
5. Test both local development and production builds
6. Ensure accessibility compliance with WCAG guidelines

## File Structure

```
src/
├── api/           # API client modules
├── components/    # Reusable React components
├── hooks/         # Custom React hooks
├── pages/         # Page components and routing
├── types/         # TypeScript type definitions
├── utils/         # Utility functions
├── constants/     # Application constants
├── styles/        # Global styles and themes
└── common/        # Shared utilities and helpers
```
