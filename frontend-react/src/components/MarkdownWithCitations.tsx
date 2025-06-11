import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ProcessedCitation, formatTimestamp } from '../utils/citationUtils';

interface MarkdownWithCitationsProps {
  content: string;
  citationMap: Map<number, ProcessedCitation>;
  onCitationClick: (citation: ProcessedCitation) => void;
}

const MarkdownWithCitations: React.FC<MarkdownWithCitationsProps> = ({
  content,
  citationMap,
  onCitationClick
}) => {
  // Handle incomplete markdown during streaming
  const safeContent = content || '';
  
  // Helper function to process text with citations
  const processTextWithCitations = (text: string): React.ReactNode[] => {
    // Debug logging
    if (text.includes('[') && text.includes(']')) {
      console.log(`🔍 Processing text with potential citations: "${text}"`);
      console.log(`🗺️ Available citations:`, Array.from(citationMap.keys()));
    }
    
    // Look for citation patterns [1], [2], etc.
    const citationRegex = /\[(\d+)\]/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(text)) !== null) {
      const citationNumber = parseInt(match[1]);
      const citation = citationMap.get(citationNumber);
      
      console.log(`🔗 Found citation marker [${citationNumber}], citation exists:`, !!citation);
      
      if (citation) {
        // Add text before citation
        if (match.index > lastIndex) {
          parts.push(text.substring(lastIndex, match.index));
        }
        
        // Add clickable citation
        parts.push(
          <button
            key={`citation-${citationNumber}-${match.index}`}
            onClick={() => onCitationClick(citation)}
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
            title={`${citation.media_name} at ${formatTimestamp(citation.timestamp)}`}
          >
            [{citationNumber}]
          </button>
        );
        
        lastIndex = match.index + match[0].length;
      }
    }
    
    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }
    
    return parts.length > 0 ? parts : [text];
  };

  try {
    return (
      <ReactMarkdown
        skipHtml={true}
        components={{
          // Custom renderer for text nodes to handle citations
          text: ({ children }) => {
            const text = children as string;
            const processedParts = processTextWithCitations(text);
            return <>{processedParts}</>;
          },
          
          // Style header elements and handle citations within them
          h1: ({ children }) => {
            const processedChildren = React.Children.map(children, child => {
              if (typeof child === 'string') {
                return processTextWithCitations(child);
              }
              return child;
            });
            return <h1 style={{ fontSize: '1.5em', fontWeight: 'bold', marginBottom: '0.5em' }}>{processedChildren}</h1>;
          },
          
          h2: ({ children }) => {
            const processedChildren = React.Children.map(children, child => {
              if (typeof child === 'string') {
                return processTextWithCitations(child);
              }
              return child;
            });
            return <h2 style={{ fontSize: '1.3em', fontWeight: 'bold', marginBottom: '0.4em' }}>{processedChildren}</h2>;
          },
          
          h3: ({ children }) => {
            const processedChildren = React.Children.map(children, child => {
              if (typeof child === 'string') {
                return processTextWithCitations(child);
              }
              return child;
            });
            return <h3 style={{ fontSize: '1.1em', fontWeight: 'bold', marginBottom: '0.3em' }}>{processedChildren}</h3>;
          },
          
          p: ({ children }) => <p style={{ marginBottom: '0.8em', lineHeight: '1.5' }}>{children}</p>,
          
          ul: ({ children }) => <ul style={{ marginLeft: '1.2em', marginBottom: '0.8em' }}>{children}</ul>,
          ol: ({ children }) => <ol style={{ marginLeft: '1.2em', marginBottom: '0.8em' }}>{children}</ol>,
          li: ({ children }) => <li style={{ marginBottom: '0.2em' }}>{children}</li>,
          
          strong: ({ children }) => <strong style={{ fontWeight: 'bold' }}>{children}</strong>,
          em: ({ children }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
          
          code: ({ children }) => (
            <code style={{
              backgroundColor: '#f1f3f4',
              padding: '2px 4px',
              borderRadius: '3px',
              fontFamily: 'monospace',
              fontSize: '0.9em'
            }}>
              {children}
            </code>
          ),
          
          pre: ({ children }) => (
            <pre style={{
              backgroundColor: '#f1f3f4',
              padding: '12px',
              borderRadius: '6px',
              overflow: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.9em',
              marginBottom: '0.8em'
            }}>
              {children}
            </pre>
          ),
          
          blockquote: ({ children }) => (
            <blockquote style={{
              borderLeft: '4px solid #e9ebed',
              paddingLeft: '1em',
              marginLeft: '0',
              fontStyle: 'italic',
              color: '#5f6368'
            }}>
              {children}
            </blockquote>
          )
        }}
      >
        {safeContent}
      </ReactMarkdown>
    );
  } catch (error) {
    // Fallback to plain text if markdown parsing fails during streaming
    console.warn('Markdown parsing failed, falling back to plain text:', error);
    
    // Clean escaped newlines in fallback content
    const cleanedContent = safeContent.replace(/\\n/g, '\n');
    const processedParts = processTextWithCitations(cleanedContent);
    
    return <div style={{ whiteSpace: 'pre-wrap' }}>{processedParts}</div>;
  }
};

export default MarkdownWithCitations;
