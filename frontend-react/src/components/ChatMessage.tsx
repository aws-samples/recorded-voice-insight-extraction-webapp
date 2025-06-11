import React from 'react';
import {
  Box,
  Container,
  SpaceBetween,
} from '@cloudscape-design/components';
import { ChatMessage as ChatMessageType } from '../types/chat';
import { ProcessedCitation, processCitations, insertCitationsAtSentences, formatTimestamp } from '../utils/citationUtils';

interface ChatMessageProps {
  message: ChatMessageType;
  isUser: boolean;
  onCitationClick?: (citation: ProcessedCitation) => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  isUser, 
  onCitationClick 
}) => {
  const messageText = message.content[0]?.text || '';
  
  // Process citations if this is an assistant message with full_answer
  let processedContent: React.ReactNode = messageText;
  let citations: ProcessedCitation[] = [];
  
  if (!isUser && message.full_answer && onCitationClick) {
    // Extract all citations from the full answer
    const allCitations = message.full_answer.answer.flatMap(part => part.citations || []);
    
    if (allCitations.length > 0) {
      citations = processCitations(allCitations);
      console.log(`📝 Processing ${citations.length} citations for message`);
      
      // Insert citation markers into the text
      const textParts = insertCitationsAtSentences(messageText, citations);
      
      processedContent = textParts.map((part, index) => {
        if (part.type === 'citation' && part.citation) {
          return (
            <button
              key={`citation-${part.citation.id}-${index}`}
              onClick={() => onCitationClick(part.citation!)}
              style={{
                background: 'none',
                border: 'none',
                color: '#0073bb',
                textDecoration: 'underline',
                cursor: 'pointer',
                padding: '0 2px',
                font: 'inherit',
                fontWeight: 'bold'
              }}
              title={`${part.citation.media_name} at ${formatTimestamp(part.citation.timestamp)}`}
            >
              {part.content}
            </button>
          );
        } else {
          return <span key={`text-${index}`}>{part.content}</span>;
        }
      });
    }
  }

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
        <SpaceBetween size="s">
          <Box 
            variant="p" 
            margin={{ top: 'xs' }}
            color={isUser ? 'inherit' : 'text-body-secondary'}
          >
            {Array.isArray(processedContent) ? (
              processedContent.map((part, index) => (
                <React.Fragment key={index}>{part}</React.Fragment>
              ))
            ) : (
              processedContent
            )}
          </Box>
          
          {/* Show citation summary for assistant messages */}
          {!isUser && citations.length > 0 && (
            <div style={{ borderTop: '1px solid #e9ebed', paddingTop: '8px' }}>
              <Box 
                variant="small" 
                color="text-body-secondary"
              >
                <strong>Sources:</strong> {citations.map(citation => (
                  <span key={citation.id}>
                    {citation.id > 1 && ', '}
                    <button
                      onClick={() => onCitationClick?.(citation)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#0073bb',
                        textDecoration: 'underline',
                        cursor: 'pointer',
                        padding: 0,
                        font: 'inherit',
                        fontSize: 'inherit'
                      }}
                      title={`${citation.media_name} at ${formatTimestamp(citation.timestamp)}`}
                    >
                      {citation.displayText} {citation.media_name} ({formatTimestamp(citation.timestamp)})
                    </button>
                  </span>
                ))}
              </Box>
            </div>
          )}
        </SpaceBetween>
      </Container>
    </Box>
  );
};

export default ChatMessage;
