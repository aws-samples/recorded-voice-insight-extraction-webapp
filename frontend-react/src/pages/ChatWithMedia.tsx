import React, { useState, useEffect } from 'react';
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

const ChatWithMediaPage: React.FC = () => {
  const [username, setUsername] = useState<string>('');
  const [authToken, setAuthToken] = useState<string>('');
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [jobData, setJobData] = useState<JobData[]>([]);
  const [selectedMediaNames, setSelectedMediaNames] = useState<MultiselectProps.Option[]>([]);
  const [authError, setAuthError] = useState<string>('');
  const [dataError, setDataError] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isSending, setIsSending] = useState<boolean>(false);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const user = await getCurrentUser();
        const session = await fetchAuthSession();
        
        if (user.username && session.tokens?.idToken) {
          setUsername(user.username);
          setAuthToken(`Bearer ${session.tokens.idToken.toString()}`);
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
      if (!isAuthenticated || !username || !authToken) return;

      try {
        setDataError('');
        const data = await retrieveAllItems(username, authToken);
        
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
  }, [isAuthenticated, username, authToken]);

  const handleMediaSelectionChange = ({ detail }: { detail: MultiselectProps.ChangeDetail }) => {
    // If user changes media selection while in conversation, clear the conversation
    if (messages.length > 0) {
      setMessages([]);
    }
    setSelectedMediaNames(detail.selectedOptions);
  };

  const handleSendMessage = async (messageText: string) => {
    if (!messageText.trim() || isSending) return;

    // Add user message to chat
    const userMessage: ChatMessageType = {
      id: Date.now().toString(),
      role: 'user',
      content: [{ text: messageText }],
    };

    setMessages(prev => [...prev, userMessage]);
    setIsSending(true);

    try {
      // TODO: Implement WebSocket streaming in Phase 4
      // For now, just add a placeholder assistant response
      setTimeout(() => {
        const assistantMessage: ChatMessageType = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: [{ text: 'This is a placeholder response. WebSocket streaming will be implemented in Phase 4.' }],
        };
        setMessages(prev => [...prev, assistantMessage]);
        setIsSending(false);
      }, 1000);
    } catch (error) {
      console.error('Error sending message:', error);
      setIsSending(false);
    }
  };

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
                disabled={isSending}
                placeholder={isSending ? "Sending..." : "Enter your question here"}
              />
            </Box>
          </SpaceBetween>
        </ContentLayout>
      }
    />
  );
};

export default ChatWithMediaPage;
