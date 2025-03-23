# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/aws-samples/recorded-voice-insight-extraction-webapp/compare/main...develop)
- Added support for non-English languages. 
  - Audio/videos for all languages supported by Amazon Transcribe are supported. 
  - Chatbot responds in the same language as the user's question, regardless the language of the source media.
- Added ability to select individual files to chat with, either 0 (chat with all files), 1 (chat with one file), or 2+ (chat with selected files).
  
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
