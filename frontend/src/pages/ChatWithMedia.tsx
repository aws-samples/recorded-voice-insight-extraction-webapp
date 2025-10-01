import React, { useState, useEffect, useCallback } from 'react';
import {
  ContentLayout,
  Header,
  SpaceBetween,
  Box,
  Multiselect,
  MultiselectProps,
  Alert,
  Spinner,
  Button,
  Checkbox,
  Select,
  SelectProps,
} from '@cloudscape-design/components';
import { getCurrentUser } from 'aws-amplify/auth';
import { fetchAuthSession } from 'aws-amplify/auth';
import BaseAppLayout from '../components/base-app-layout';
import { retrieveAllItems } from '../api/database';
import { getMediaPresignedUrl } from '../api/s3';
import { JobData, ChatMessage as ChatMessageType } from '../types/chat';
import { ProcessedCitation } from '../utils/citationUtils';
import { urlDecodeFilename } from '../utils/fileUtils';
import ChatContainer from '../components/ChatContainer';
import ChatInput from '../components/ChatInput';
import MediaPlayer from '../components/MediaPlayer';
import { chatWebSocketService } from '../api/websocket';
import { SUPPORTED_LANGUAGES, SupportedLanguage } from '../constants/languages';

const ChatWithMediaPage: React.FC = () => {
  const [username, setUsername] = useState<string>('');
  const [idToken, setIdToken] = useState<string>(''); // For REST API calls
  const [accessToken, setAccessToken] = useState<string>(''); // For WebSocket calls
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [jobData, setJobData] = useState<JobData[]>([]);
  const [selectedMediaNames, setSelectedMediaNames] = useState<MultiselectProps.Option[]>([]);
  const [authError, setAuthError] = useState<string>('');
  const [dataError, setDataError] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [streamingError, setStreamingError] = useState<string>('');
  const [selectedCitation, setSelectedCitation] = useState<ProcessedCitation | null>(null);
  const [isMediaPlayerVisible, setIsMediaPlayerVisible] = useState<boolean>(false);
  const [displaySubtitles, setDisplaySubtitles] = useState<boolean>(false);
  const [translationLanguage, setTranslationLanguage] = useState<SelectProps.Option | null>(null);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const user = await getCurrentUser();
        const session = await fetchAuthSession();
        
        if (user.username && session.tokens?.idToken && session.tokens?.accessToken) {
          setUsername(user.username);
          setIdToken(`Bearer ${session.tokens.idToken.toString()}`);
          setAccessToken(session.tokens.accessToken.toString());
          setIsAuthenticated(true);
        } else {
          setAuthError('Authentication required. Please log in.');
        }
      } catch (err) {
        console.error('Authentication error:', err);
        setAuthError('Authentication failed. Please log in.');
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  useEffect(() => {
    const fetchJobData = async () => {
      if (!isAuthenticated || !username || !idToken) return;

      try {
        setDataError('');
        const data = await retrieveAllItems(username);
        
        const completedJobs = data.filter(
          job => job.job_status === 'Completed' || job.job_status === 'BDA Analysis Complete'
        );
        
        setJobData(completedJobs);
      } catch (error) {
        console.error('Error fetching job data:', error);
        setDataError('Failed to load media files. Please try refreshing the page.');
      }
    };

    fetchJobData();
  }, [isAuthenticated, username, idToken]);

  const handleMediaSelectionChange = ({ detail }: any) => {
    if (messages.length > 0) {
      setMessages([]);
    }
    setSelectedMediaNames(detail.selectedOptions);
  };

  const handleSubtitleToggle = ({ detail }: any) => {
    setDisplaySubtitles(detail.checked);
    if (!detail.checked) {
      setTranslationLanguage(null);
    }
  };

  const handleLanguageChange = ({ detail }: any) => {
    setTranslationLanguage(detail.selectedOption);
  };

  const handleCitationClick = (citation: ProcessedCitation) => {
    setSelectedCitation(citation);
    setIsMediaPlayerVisible(true);
  };

  const handleGetPresignedUrl = useCallback(async (mediaName: string) => {
    try {
      return await getMediaPresignedUrl(mediaName, username);
    } catch (error) {
      console.error('Error getting presigned URL:', error);
      throw new Error('Failed to get media URL. Please try again.');
    }
  }, [username]);

  const handleSendMessage = useCallback(async (messageText: string) => {
    if (!messageText.trim() || isSending) return;

    setStreamingError('');

    const userMessage: ChatMessageType = {
      id: Date.now().toString(),
      role: 'user',
      content: [{ text: messageText }],
    };

    setMessages(prev => [...prev, userMessage]);
    setIsSending(true);

    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: ChatMessageType = {
      id: assistantMessageId,
      role: 'assistant',
      content: [{ text: '' }],
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      await chatWebSocketService.connect(accessToken);

      const mediaNames = selectedMediaNames.map(option => option.value as string);
      
      // For single media file selection, we need to pass the transcript job ID (UUID)
      let transcriptJobId: string | undefined = undefined;
      if (mediaNames.length === 1) {
        const selectedJob = jobData.find(job => job.media_name === mediaNames[0]);
        if (selectedJob) {
          transcriptJobId = selectedJob.UUID;
          console.log(`Selected single media file: ${mediaNames[0]}, Job ID: ${transcriptJobId}`);
        } else {
          console.error(`Could not find job data for selected media: ${mediaNames[0]}`);
        }
      }
      
      const responseGenerator = await chatWebSocketService.sendMessage(
        [...messages, userMessage],
        username,
        accessToken,
        mediaNames,
        transcriptJobId
      );

      let fullAnswer = '';
      let lastFullQAnswer = null;

      for await (const partialResponse of responseGenerator) {
        lastFullQAnswer = partialResponse;
        
        // Don't build fullAnswer from concatenated text - let the ChatMessage component
        // handle the markdown rendering directly from the partialResponse structure
        if (partialResponse.answer && partialResponse.answer.length > 0) {
          // Build display text for the content field (this is mainly for debugging/fallback)
          fullAnswer = partialResponse.answer
            .map(part => part.partial_answer || '')
            .join('');
        }

        // Update the message with the streaming partialResponse
        // The ChatMessage component will handle markdown rendering from this structure
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessageId 
            ? {
                ...msg,
                content: [{ text: fullAnswer }], // Keep this for fallback, but ChatMessage uses full_answer
                full_answer: partialResponse     // This is what drives the markdown rendering
              }
            : msg
        ));
      }

      // Final update is the same since we're already including full_answer during streaming
      if (lastFullQAnswer) {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessageId 
            ? {
                ...msg,
                content: [{ text: fullAnswer }],
                full_answer: lastFullQAnswer
              }
            : msg
        ));
      }

    } catch (error) {
      console.error('Error sending message:', error);
      
      let errorMessage = 'An error occurred while processing your request.';
      
      if (error instanceof Error) {
        errorMessage = error.message;
      }

      setStreamingError(errorMessage);
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId));
    } finally {
      setIsSending(false);
    }
  }, [isSending, accessToken, selectedMediaNames, messages, username, jobData]);

  const handleClearConversation = () => {
    setMessages([]);
  };

  const mediaOptions: MultiselectProps.Option[] = jobData
    .map(job => ({
      label: urlDecodeFilename(job.media_name),
      value: job.media_name,
    }))
    .sort((a, b) => a.label.localeCompare(b.label));

  if (isLoading) {
    return (
      <BaseAppLayout
        content={
          <ContentLayout
            header={
              <Header variant="h1">
                Chat With Your Media
              </Header>
            }
          >
            <Box textAlign="center" padding="xxl">
              <Spinner size="large" />
              <Box variant="p" margin={{ top: "m" }}>
                Loading...
              </Box>
            </Box>
          </ContentLayout>
        }
      />
    );
  }

  if (!isAuthenticated || authError) {
    return (
      <BaseAppLayout
        content={
          <ContentLayout
            header={
              <Header variant="h1">
                Chat With Your Media
              </Header>
            }
          >
            <Alert type="error" header="Authentication Required">
              {authError || 'Please log in to continue.'}
            </Alert>
          </ContentLayout>
        }
      />
    );
  }

  return (
    <BaseAppLayout
      content={
        <ContentLayout
          header={
            <Header
              variant="h1"
              description="Chat with your uploaded media files using AI"
              actions={
                messages.length > 0 ? (
                  <Button
                    variant="normal"
                    onClick={handleClearConversation}
                  >
                    Clear Conversation
                  </Button>
                ) : undefined
              }
            >
              Chat With Your Media
            </Header>
          }
        >
          <SpaceBetween size="l">
            {[
              dataError && (
                <Alert key="data-error" type="error" dismissible onDismiss={() => setDataError('')}>
                  {dataError}
                </Alert>
              ),

              streamingError && (
                <Alert key="streaming-error" type="error" dismissible onDismiss={() => setStreamingError('')}>
                  {streamingError}
                </Alert>
              ),
              
              <Box key="media-selection">
                <Header variant="h3" description="Leave blank to chat with all media files">
                  Select media file(s) to chat with
                </Header>
                <SpaceBetween size="s">
                  <Multiselect
                    selectedOptions={selectedMediaNames}
                    onChange={handleMediaSelectionChange}
                    options={mediaOptions}
                    placeholder="Chat with all media files"
                    empty="No completed media files available"
                    filteringType="auto"
                    disabled={isSending}
                  />
                  
                  <SpaceBetween size="s" direction="horizontal">
                    <Checkbox
                      checked={displaySubtitles}
                      onChange={handleSubtitleToggle}
                      disabled={isSending}
                    >
                      Display subtitles in videos
                    </Checkbox>
                    
                    {displaySubtitles && (
                      <Select
                        selectedOption={translationLanguage}
                        onChange={handleLanguageChange}
                        options={SUPPORTED_LANGUAGES.map(lang => ({
                          label: lang,
                          value: lang
                        }))}
                        placeholder="Translate subtitles?"
                        disabled={isSending}
                        expandToViewport
                      />
                    )}
                  </SpaceBetween>
                </SpaceBetween>
              </Box>,
              
              // Only show chat container if there are messages
              messages.length > 0 && (
                <Box key="chat-container">
                  <ChatContainer 
                    messages={messages} 
                    onCitationClick={handleCitationClick}
                  />
                </Box>
              ),
              
              <Box key="chat-input">
                <ChatInput
                  onSendMessage={handleSendMessage}
                  disabled={isSending}
                  placeholder={
                    isSending
                      ? "Processing..."
                      : "Enter your question here"
                  }
                />
              </Box>
            ].filter(Boolean)}
          </SpaceBetween>

          <MediaPlayer
            citation={selectedCitation}
            isVisible={isMediaPlayerVisible}
            onClose={() => {
              setIsMediaPlayerVisible(false);
              setSelectedCitation(null);
            }}
            onGetPresignedUrl={handleGetPresignedUrl}
            displaySubtitles={displaySubtitles}
            translationLanguage={translationLanguage?.value as SupportedLanguage}
            username={username}
            idToken={idToken}
            jobData={jobData}
          />
        </ContentLayout>
      }
    />
  );
};

export default ChatWithMediaPage;
