import React from 'react';
import {
  Box,
  Container,
} from '@cloudscape-design/components';
import { ChatMessage as ChatMessageType } from '../types/chat';
import { ProcessedCitation, processPartialAnswersForMarkdown, extractAllCitations, formatTimestamp } from '../utils/citationUtils';
import { urlDecodeFilename } from '../utils/fileUtils';
import MarkdownWithCitations from './MarkdownWithCitations';

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
  let allCitations: ProcessedCitation[] = [];
  
  if (!isUser) {
    // For assistant messages, always render as markdown
    if (message.full_answer && onCitationClick) {
      const partialAnswers = message.full_answer.answer || [];
      
      if (partialAnswers.length > 0) {
        // Process partial answers for markdown rendering
        const { markdownContent, citationMap } = processPartialAnswersForMarkdown(partialAnswers);
        
        // Extract all citations for the sources section
        allCitations = extractAllCitations(partialAnswers);
        
        // Render markdown with citations
        processedContent = (
          <div>
            <MarkdownWithCitations
              content={markdownContent}
              citationMap={citationMap}
              onCitationClick={onCitationClick}
            />
          </div>
        );
      } else {
        // Fallback to plain markdown if no partial answers but we have full_answer
        processedContent = (
          <div>
            <MarkdownWithCitations
              content={messageText}
              citationMap={new Map()}
              onCitationClick={onCitationClick}
            />
          </div>
        );
      }
    } else {
      // For assistant messages without full_answer or citations, still render as markdown
      processedContent = (
        <div>
          <MarkdownWithCitations
            content={messageText}
            citationMap={new Map()}
            onCitationClick={onCitationClick || (() => {})}
          />
        </div>
      );
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
        <div>
          <Box 
            key="message-content"
            variant="div"
            color={isUser ? 'inherit' : 'text-body-secondary'}
          >
            {isUser ? messageText : processedContent}
          </Box>
          
          {/* Show citation summary for assistant messages */}
          {!isUser && allCitations.length > 0 && (
            <div key="citation-sources" style={{ borderTop: '1px solid #e9ebed', paddingTop: '8px', marginTop: '8px' }}>
              <Box 
                variant="small" 
                color="text-body-secondary"
              >
                <strong>Sources:</strong> {allCitations.map((citation, index) => (
                  <span key={`citation-${citation.id}-${citation.media_name}-${citation.timestamp}`}>
                    {index > 0 && ', '}
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
                      title={`${urlDecodeFilename(citation.media_name)} at ${formatTimestamp(citation.timestamp)}`}
                    >
                      {citation.displayText} {urlDecodeFilename(citation.media_name)} ({formatTimestamp(citation.timestamp)})
                    </button>
                  </span>
                ))}
              </Box>
            </div>
          )}
        </div>
      </Container>
    </Box>
  );
};

export default ChatMessage;
