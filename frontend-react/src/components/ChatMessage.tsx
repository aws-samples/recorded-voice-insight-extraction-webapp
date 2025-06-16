import React from 'react';
import {
  Box,
  Container,
  SpaceBetween,
} from '@cloudscape-design/components';
import { ChatMessage as ChatMessageType } from '../types/chat';
import { ProcessedCitation, processPartialAnswersForMarkdown, extractAllCitations, formatTimestamp } from '../utils/citationUtils';
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
        console.log(`📝 Processing ${partialAnswers.length} partial answers with citations for markdown`);
        
        // Process partial answers for markdown rendering
        const { markdownContent, citationMap } = processPartialAnswersForMarkdown(partialAnswers);
        
        // Extract all citations for the sources section
        allCitations = extractAllCitations(partialAnswers);
        
        console.log(`📚 Total citations found: ${allCitations.length}`);
        console.log(`📄 Markdown content preview: ${markdownContent.substring(0, 500)}...`);
        console.log(`🗺️ Citation map size: ${citationMap.size}`);
        console.log(`🔗 Citation map keys: [${Array.from(citationMap.keys()).join(', ')}]`);
        
        // Render markdown with citations
        processedContent = (
          <div>
            <div style={{ background: '#fff3cd', padding: '4px', fontSize: '12px', marginBottom: '8px' }}>
              DEBUG: Using MarkdownWithCitations - Citations: {citationMap.size}, Content length: {markdownContent.length}
            </div>
            <MarkdownWithCitations
              content={markdownContent}
              citationMap={citationMap}
              onCitationClick={onCitationClick}
            />
          </div>
        );
      } else {
        console.log(`⚠️ No partial answers found, using fallback markdown`);
        // Fallback to plain markdown if no partial answers but we have full_answer
        processedContent = (
          <div>
            <div style={{ background: '#f8d7da', padding: '4px', fontSize: '12px', marginBottom: '8px' }}>
              DEBUG: Using fallback MarkdownWithCitations - No partial answers
            </div>
            <MarkdownWithCitations
              content={messageText}
              citationMap={new Map()}
              onCitationClick={onCitationClick}
            />
          </div>
        );
      }
    } else {
      console.log(`⚠️ No full_answer or onCitationClick, using basic markdown`);
      // For assistant messages without full_answer or citations, still render as markdown
      processedContent = (
        <div>
          <div style={{ background: '#d1ecf1', padding: '4px', fontSize: '12px', marginBottom: '8px' }}>
            DEBUG: Using basic MarkdownWithCitations - No full_answer
          </div>
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
        <SpaceBetween size="s">
          <Box 
            variant="div" 
            margin={{ top: 'xs' }}
            color={isUser ? 'inherit' : 'text-body-secondary'}
          >
            {isUser ? messageText : processedContent}
          </Box>
          
          {/* Show citation summary for assistant messages */}
          {!isUser && allCitations.length > 0 && (
            <div style={{ borderTop: '1px solid #e9ebed', paddingTop: '8px' }}>
              <Box 
                variant="small" 
                color="text-body-secondary"
              >
                <strong>Sources:</strong> {allCitations.map(citation => (
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
