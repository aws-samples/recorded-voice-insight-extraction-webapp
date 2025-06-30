# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/compare/main...develop)

## [1.3.1](https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/releases/tag/v1.3.1) - 2025-06-30

### ✨ New Features
- Replaced [seconds] time format in all LLM prompts to enable chatbot to answer questions like "summarize what happens in the first 15 minutes" without having to do internal math converting 15 minutes to 900 seconds.

### 🐛 Bug Fixes
- Bug fix related to opensearch py library updating without backwards compatibility ([this issue](https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/issues/7)).

## [1.3.0](https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/releases/tag/v1.3.0) - 2025-06-23

### 🚀 Major Architecture Changes
- **Complete Frontend Replacement**: Replaced Streamlit application with modern React single-page application
  - Removed ECS Fargate deployment with Application Load Balancer
  - New React frontend deployed to S3 behind CloudFront distribution
  - Significantly improved user experience with modern UI components
  - Better responsive design and mobile compatibility
- **Enhanced API Architecture**: Improved REST API with comprehensive OpenAPI documentation
  - Added new `/analysis-templates` CRUD endpoints for template management
  - Enhanced DynamoDB operations with additional actions for BDA mapping and template management
  - Updated API documentation with complete OpenAPI 3.0 specification

### 🔐 Authentication & WebSocket Improvements
- **WebSocket Authentication Overhaul**: 
  - Removed WebSocket authorizer lambda (`ws-authorizer-lambda.py`)
  - Authentication now handled in message bodies rather than connection headers
  - Improved session management with DynamoDB-based WebSocket session tracking
  - Added support for chunked WebSocket messages for large responses
  - Enhanced connection reliability and error handling

### ✨ New Features
- **Analysis Templates Management**:
  - Added user-customizable analysis templates stored in DynamoDB
  - Users can create, update, and delete custom analysis templates via UI
  - Default templates automatically populated on deployment
  - Templates support custom system prompts, model selection, and Bedrock parameters
  - Migrated from CSV-based templates to database-driven approach
- **Enhanced CORS Support**: Added comprehensive CORS utilities for better API integration
- **Improved Error Handling**: Enhanced error responses across all API endpoints
- **Development Tools**: Added Makefile for streamlined development workflows

### 🔧 Technical Improvements
- **Lambda Function Enhancements**:
  - New analysis templates lambda for CRUD operations
  - Enhanced DDB handler with additional actions for template and BDA mapping management
  - Improved WebSocket handler with chunked message support
  - Updated LLM handler with Converse API for better model compatibility
- **Infrastructure Updates**:
  - Updated CDK stacks for React frontend deployment
  - Enhanced API Gateway configuration with improved throttling and logging
  - Added SSM Parameter Store integration for frontend configuration
  - Improved security with updated IAM policies and permissions

### 📚 Documentation Updates
- **Comprehensive API Documentation**: 
  - Complete OpenAPI 3.0 specification with all endpoints documented
  - Updated API README with WebSocket authentication changes
  - Added detailed examples for REST and WebSocket API usage
  - Included JavaScript/Browser WebSocket examples
- **Architecture Documentation**: Updated architecture diagrams and descriptions
- **Development Documentation**: Added Amazon Q Developer configurations and development guidelines

### 🗑️ Removed
- **Streamlit Frontend**: Completely removed Streamlit-based frontend
  - Removed Docker containerization for frontend
  - Removed ECS Fargate deployment stack
  - Removed Application Load Balancer configuration
  - Removed Streamlit-specific Python dependencies and components
- **Legacy Components**: Removed outdated WebSocket authorizer and associated infrastructure
- **Analysis Result Caching**: Removed DynamoDB caching of analysis results to simplify codebase

### 🐛 Bug Fixes
- Fixed CORS issues with proxy server configuration for local development
- Improved WebSocket connection stability and error handling
- Enhanced presigned URL generation for file operations
- Fixed various UI/UX issues and improved responsive design

### 🔄 Migration Notes
- **Breaking Change**: Frontend completely replaced - existing Streamlit customizations will need to be migrated to React
- **API Compatibility**: REST API endpoints remain backward compatible
- **WebSocket Changes**: WebSocket authentication method changed - clients need to include username in message body instead of connection headers
- **Configuration**: Some configuration parameters may need adjustment for new frontend deployment model

## [1.2.0](https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/releases/tag/v1.2.0) - 2025-05-27
- Added support for non-English languages. 
  - Audio/videos for all languages supported by Amazon Transcribe are supported. 
  - Chatbot responds in the same language as the user's question, regardless the language of the source media.
  - Added ability to display subtitles in videos, including translating them to any language of your choice.
- Added ability to select individual files to chat with, either 0 (chat with all files), 1 (chat with one file), or 2+ (chat with selected files).
- Added improved knowledge base syncing mechanism leveraging [file-by-file ingestion](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-direct-ingestion-add.html) rather than entire-KB sync, simplifying backend architecture and improving application scalability.
- Added "File Management" page which allows users to delete files they have uploaded (and knowledge base is synced accordingly).
- Added integration with Bedrock Data Automation (BDA). Users can select to enable BDA on a per-file basis at upload time. When chatting with that file, the BDA output is included in the LLM prompt so users will be able to ask questions like "what words were shown on the screen in this video". This information is not yet included in the knowledge base, and therefore is only used when chatting with a single video (as opposed to multiple videos and/or all videos in a RAG scenario).
- Improved output parsing of streaming LLM generated strings to make UI more robust to different LLM response structures (Nova, Claude, etc).
- Misc bug fixes

  
## [1.1.0](https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/releases/tag/v1.1.0) - 2025-02-12
### Added 
- This Changelog file
- Websocket API through API Gateway to stream LLM responses
  - Client provides cognito-generated access token in websocket connection header, lambda authorizer validates token
  - Improved parsing logic to display streaming (incomplete) json to streamlit UI

### Removed
- Non-streaming generation in Chat With Your Media page

### Fixed
- Bug occurring when > 10 messages are sent
- Bug related to deploying application from mac OS (docker)

## [1.0.0](https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/releases/tag/v1.0.0) - 2025-01-20
- Initial release


[1.1.0]: https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/releases/tag/v1.1.0
[1.0.0]: https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/releases/tag/v1.0.0
