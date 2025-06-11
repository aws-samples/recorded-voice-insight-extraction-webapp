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
} from '@cloudscape-design/components';
import { getCurrentUser } from 'aws-amplify/auth';
import { fetchAuthSession } from 'aws-amplify/auth';
import BaseAppLayout from '../components/base-app-layout';
import { retrieveAllItems } from '../api/database';
import { JobData, ChatMessage as ChatMessageType } from '../types/chat';
import ChatContainer from '../components/ChatContainer';
import ChatInput from '../components/ChatInput';
import { chatWebSocketService, WebSocketTimeoutError } from '../api/websocket';

const ChatWithMediaPage: React.FC = () => {
  const [username, setUsername] = useState<string>('');
  const [idToken, setIdToken] = useState<string>(''); // For REST API calls
  const [accessToken, setAccessToken] = useState<string>(''); // For WebSocket calls (raw token)
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [jobData, setJobData] = useState<JobData[]>([]);
  const [selectedMediaNames, setSelectedMediaNames] = useState<MultiselectProps.Option[]>([]);
  const [authError, setAuthError] = useState<string>('');
  const [dataError, setDataError] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [streamingError, setStreamingError] = useState<string>('');

  useEffect(() => {
    const initAuth = async () => {
      try {
        const user = await getCurrentUser();
        const session = await fetchAuthSession();
        console.log('Access token type check:', session.tokens?.accessToken?.toString().substring(0, 50));
        
        if (user.username && session.tokens?.idToken && session.tokens?.accessToken) {
          setUsername(user.username);
          // Store both tokens for different API types
          setIdToken(`Bearer ${session.tokens.idToken.toString()}`); // For REST API
          setAccessToken(session.tokens.accessToken.toString()); // For WebSocket API (no Bearer prefix)
          
          // DEBUG: Log tokens for testing
          console.log('=== TOKEN DEBUG INFO ===');
          console.log('ACCESS TOKEN (for WebSocket):', session.tokens.accessToken.toString());
          console.log('ACCESS TOKEN Length:', session.tokens.accessToken.toString().length);
          console.log('ID TOKEN (for REST API):', session.tokens.idToken.toString());
          console.log('ID TOKEN Length:', session.tokens.idToken.toString().length);
          console.log('========================');
          
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
        // Use ID token for REST API calls
        const data = await retrieveAllItems(username, idToken);
        
        // Filter for completed jobs only (matching Streamlit behavior)
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
    // If user changes media selection while in conversation, clear the conversation
    if (messages.length > 0) {
      setMessages([]);
    }
    setSelectedMediaNames(detail.selectedOptions);
  };

  const handleSendMessage = useCallback(async (messageText: string) => {
    if (!messageText.trim() || isSending) return;

    // Clear any previous streaming errors
    setStreamingError('');

    // Add user message to chat
    const userMessage: ChatMessageType = {
      id: Date.now().toString(),
      role: 'user',
      content: [{ text: messageText }],
    };

    setMessages(prev => [...prev, userMessage]);
    setIsSending(true);

    // Create assistant message placeholder for streaming
    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: ChatMessageType = {
      id: assistantMessageId,
      role: 'assistant',
      content: [{ text: '' }],
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Connect to WebSocket if not already connected (use access token)
      await chatWebSocketService.connect(accessToken);

      // Get selected media names and determine transcript job ID
      const mediaNames = selectedMediaNames.map(option => option.value as string);
      
      // For single media file selection, we need to pass the transcript job ID (UUID)
      let transcriptJobId: string | undefined = undefined;
      if (mediaNames.length === 1) {
        // Find the job data for the selected media file
        const selectedJob = jobData.find(job => job.media_name === mediaNames[0]);
        if (selectedJob) {
          transcriptJobId = selectedJob.UUID;
          console.log(`Selected single media file: ${mediaNames[0]}, Job ID: ${transcriptJobId}`);
        } else {
          console.error(`Could not find job data for selected media: ${mediaNames[0]}`);
        }
      }
      
      // Send message and get streaming response
      const responseGenerator = await chatWebSocketService.sendMessage(
        [...messages, userMessage],
        username,
        accessToken, // Pass the access token for authentication
        mediaNames,
        transcriptJobId  // Pass the job ID for single file queries
      );

      let fullAnswer = '';
      let lastFullQAnswer = null;

      // Process streaming responses
      for await (const partialResponse of responseGenerator) {
        lastFullQAnswer = partialResponse;
        
        // Extract text from the response
        if (partialResponse.answer && partialResponse.answer.length > 0) {
          const latestPartial = partialResponse.answer[partialResponse.answer.length - 1];
          if (latestPartial.partial_answer) {
            fullAnswer = partialResponse.answer
              .map(part => part.partial_answer)
              .join('');
          }
        }

        // Update the assistant message with streaming content
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessageId 
            ? {
                ...msg,
                content: [{ text: fullAnswer }],
                full_answer: partialResponse
              }
            : msg
        ));
      }

      // Final update with complete response
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
      
      if (error instanceof WebSocketTimeoutError) {
        errorMessage = 'Request timed out. Please try again with a shorter question or fewer media files.';
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }

      setStreamingError(errorMessage);

      // Remove the empty assistant message on error
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId));
    } finally {
      setIsSending(false);
    }
  }, [isSending, accessToken, selectedMediaNames, messages, username]);

  const handleClearConversation = () => {
    setMessages([]);
  };

  // Create options for the multiselect from job data
  const mediaOptions: MultiselectProps.Option[] = jobData
    .map(job => ({
      label: job.media_name,
      value: job.media_name,
    }))
    .sort((a, b) => a.label.localeCompare(b.label)); // Sort alphabetically

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
            {dataError && (
              <Alert type="error" dismissible onDismiss={() => setDataError('')}>
                {dataError}
              </Alert>
            )}

            {streamingError && (
              <Alert type="error" dismissible onDismiss={() => setStreamingError('')}>
                {streamingError}
              </Alert>
            )}
            
            <Box>
              <Header variant="h3" description="Select media files to analyze">
                Pick media file to analyze:
              </Header>
              <Multiselect
                selectedOptions={selectedMediaNames}
                onChange={handleMediaSelectionChange}
                options={mediaOptions}
                placeholder="Chat with all media files"
                empty="No completed media files available"
                filteringType="auto"
                disabled={isSending}
              />
              {selectedMediaNames.length > 0 && (
                <Box variant="small" margin={{ top: "xs" }} color="text-body-secondary">
                  Selected: {selectedMediaNames.map(option => option.label).join(', ')}
                </Box>
              )}
            </Box>
            
            <Box>
              <ChatContainer messages={messages} />
            </Box>
            
            <Box>
              <ChatInput
                onSendMessage={handleSendMessage}
                disabled={isSending || selectedMediaNames.length === 0}
                placeholder={
                  selectedMediaNames.length === 0
                    ? "Select media files to start chatting"
                    : isSending
                    ? "Processing..."
                    : "Enter your question here"
                }
              />
            </Box>
          </SpaceBetween>
        </ContentLayout>
      }
    />
  );
};

export default ChatWithMediaPage;
