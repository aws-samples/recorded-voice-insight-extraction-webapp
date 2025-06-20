import React, { useEffect, useRef } from 'react';
import { Box } from '@cloudscape-design/components';
import { ChatMessage as ChatMessageType } from '../types/chat';
import { ProcessedCitation } from '../utils/citationUtils';
import ChatMessage from './ChatMessage';

interface ChatContainerProps {
  messages: ChatMessageType[];
  onCitationClick?: (citation: ProcessedCitation) => void;
}

const ChatContainer: React.FC<ChatContainerProps> = ({ 
  messages,
  onCitationClick
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div
      ref={containerRef}
      className="chat-container"
      style={{
        maxHeight: '600px',
        overflowY: 'auto',
        border: '1px solid var(--awsui-color-border-divider-default)',
        borderRadius: '4px',
        backgroundColor: 'var(--awsui-color-background-container-content)'
      }}
    >
      <Box padding="s">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            isUser={message.role === 'user'}
            onCitationClick={onCitationClick}
          />
        ))}
      </Box>
    </div>
  );
};

export default ChatContainer;
