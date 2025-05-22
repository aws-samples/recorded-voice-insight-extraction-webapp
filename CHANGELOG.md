# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/compare/main...develop)
- Added support for non-English languages. 
  - Audio/videos for all languages supported by Amazon Transcribe are supported. 
  - Chatbot responds in the same language as the user's question, regardless the language of the source media.
  - Added ability to display subtitles in videos, including translating them to any language of your choice.
- Added ability to select individual files to chat with, either 0 (chat with all files), 1 (chat with one file), or 2+ (chat with selected files).
- Added improved knowledge base syncing mechanism leveraging [file-by-file ingestion](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-direct-ingestion-add.html) rather than entire-KB sync, simplifying backend architecture and improving application scalability.
- Added "File Management" page which allows users to delete files they have uploaded (and knowledge base is synced accordingly).
- Added integration with Bedrock Data Automation (BDA). Users can select to enable BDA on a per-file basis at upload time. When chatting with that file, the BDA output is included in the LLM prompt so users will be able to ask questions like "what words were shown on the screen in this video". This information is not yet included in the knowledge base, and therefore is only used when chatting with a single video (as opposed to multiple videos and/or all videos in a RAG scenario).
- Improved output parsing of streaming LLM generated strings to make UI more robust to different LLM response structures (Nova, Claude, etc).

  
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
