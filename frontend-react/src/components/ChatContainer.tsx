import React, { useEffect, useRef } from 'react';
import {
  Box,
  Container,
  SpaceBetween,
} from '@cloudscape-design/components';
import { ChatMessage as ChatMessageType } from '../types/chat';
import ChatMessage from './ChatMessage';

interface ChatContainerProps {
  messages: ChatMessageType[];
}

const ChatContainer: React.FC<ChatContainerProps> = ({ messages }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  if (messages.length === 0) {
    return (
      <Container>
        <Box 
          textAlign="center" 
          padding="xxl" 
          color="text-body-secondary"
        >
          <Box variant="h3" margin={{ bottom: 's' }}>
            Start a conversation
          </Box>
          <Box variant="p">
            Ask questions about your uploaded media files. The AI will provide answers with citations that link to specific timestamps in your recordings.
          </Box>
        </Box>
      </Container>
    );
  }

  return (
    <Container>
      <Box padding="m">
        <SpaceBetween direction="vertical" size="m">
          {messages.map((message, index) => (
            <ChatMessage
              key={message.id || index}
              message={message}
              isUser={message.role === 'user'}
            />
          ))}
          <div ref={messagesEndRef} />
        </SpaceBetween>
      </Box>
    </Container>
  );
};

export default ChatContainer;
