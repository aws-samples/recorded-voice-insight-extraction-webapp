import React from 'react';
import {
  Box,
  Container,
  SpaceBetween,
} from '@cloudscape-design/components';
import { ChatMessage as ChatMessageType } from '../types/chat';

interface ChatMessageProps {
  message: ChatMessageType;
  isUser: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, isUser }) => {
  const messageText = message.content[0]?.text || '';

  return (
    <Box margin={{ bottom: 'm' }}>
      <Container
        variant={isUser ? 'default' : 'stacked'}
        header={
          <Box 
            fontSize="body-s" 
            fontWeight="bold" 
            color={isUser ? 'text-status-info' : 'text-status-success'}
          >
            {isUser ? 'You' : 'Assistant'}
          </Box>
        }
      >
        <Box 
          variant="p" 
          margin={{ top: 'xs' }}
          color={isUser ? 'inherit' : 'text-body-secondary'}
        >
          {messageText}
        </Box>
      </Container>
    </Box>
  );
};

export default ChatMessage;
