import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ProcessedCitation, formatTimestamp } from '../utils/citationUtils';
import { urlDecodeFilename } from '../utils/fileUtils';

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
  
  // Create the citation button component
  const CitationButton: React.FC<{ citationNumber: number }> = ({ citationNumber }) => {
    const citation = citationMap.get(citationNumber);
    const [hoverTimeout, setHoverTimeout] = React.useState<number | null>(null);
    const [lastTriggered, setLastTriggered] = React.useState<number>(0);
    
    if (!citation) {
      return <span>[{citationNumber}]</span>;
    }
    
    const handleCitationTrigger = () => {
      const now = Date.now();
      const cooldownPeriod = 2000; // 2 seconds cooldown
      
      if (now - lastTriggered < cooldownPeriod) {
        console.log(`🕒 Citation [${citationNumber}] still in cooldown period`);
        return;
      }
      
      console.log(`🎯 Citation [${citationNumber}] triggered!`);
      setLastTriggered(now);
      onCitationClick(citation);
    };
    
    const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
      e.currentTarget.style.background = '#d1e7f7';
      e.currentTarget.style.transform = 'translateY(-1px)';
      
      // Set a delay before triggering the citation
      const timeout = setTimeout(() => {
        console.log(`🎯 Citation [${citationNumber}] hover delay completed - showing media!`);
        handleCitationTrigger();
      }, 1000); // 1000ms delay (1 second)
      
      setHoverTimeout(timeout);
    };
    
    const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
      e.currentTarget.style.background = '#e8f4fd';
      e.currentTarget.style.transform = 'translateY(0)';
      
      // Cancel the pending hover action if mouse leaves
      if (hoverTimeout) {
        console.log(`🚫 Citation [${citationNumber}] hover cancelled - mouse left before delay`);
        clearTimeout(hoverTimeout);
        setHoverTimeout(null);
      }
    };
    
    // Cleanup timeout on unmount
    React.useEffect(() => {
      return () => {
        if (hoverTimeout) {
          clearTimeout(hoverTimeout);
        }
      };
    }, [hoverTimeout]);
    
    return (
      <button
        onClick={handleCitationTrigger}
        style={{
          background: '#e8f4fd',
          border: '1px solid #0073bb',
          borderRadius: '4px',
          color: '#0073bb',
          cursor: 'pointer',
          padding: '2px 6px',
          font: 'inherit',
          fontSize: '0.9em',
          fontWeight: 'bold',
          textDecoration: 'none',
          display: 'inline-block',
          margin: '0 2px',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        title={`Hover to preview: ${urlDecodeFilename(citation.media_name)} at ${formatTimestamp(citation.timestamp)}`}
      >
        {citationNumber}
      </button>
    );
  };

  // Process content by rendering markdown first, then post-processing for citations
  const renderContentWithCitations = (): React.ReactNode => {
    console.log(`🔄 Processing content for citations. Content length: ${safeContent.length}`);
    console.log(`🗺️ Available citations:`, Array.from(citationMap.keys()));
    
    // Split content by citation markers to create an array of text and citation parts
    const citationRegex = /\[(\d+)\]/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;
    let citationCount = 0;

    while ((match = citationRegex.exec(safeContent)) !== null) {
      const citationNumber = parseInt(match[1]);
      const citation = citationMap.get(citationNumber);
      
      console.log(`🔗 Found citation marker [${citationNumber}] at position ${match.index}, citation exists:`, !!citation);
      
      if (citation) {
        citationCount++;
        
        // Add text before citation (render as markdown)
        if (match.index > lastIndex) {
          const textBefore = safeContent.substring(lastIndex, match.index);
          if (textBefore.trim()) {
            parts.push(
              <ReactMarkdown
                key={`text-before-${match.index}`}
                skipHtml={true}
                components={{
                  p: ({ children }) => <span>{children}</span>, // Inline rendering
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
                }}
              >
                {textBefore}
              </ReactMarkdown>
            );
          }
        }
        
        // Add clickable citation
        parts.push(
          <CitationButton key={`citation-${citationNumber}-${match.index}`} citationNumber={citationNumber} />
        );
        
        lastIndex = match.index + match[0].length;
      } else {
        console.log(`❌ Citation [${citationNumber}] not found in citation map`);
      }
    }
    
    // Add remaining text (render as markdown)
    if (lastIndex < safeContent.length) {
      const remainingText = safeContent.substring(lastIndex);
      if (remainingText.trim()) {
        parts.push(
          <ReactMarkdown
            key={`text-remaining-${lastIndex}`}
            skipHtml={true}
            components={{
              p: ({ children }) => <span>{children}</span>, // Inline rendering
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
            }}
          >
            {remainingText}
          </ReactMarkdown>
        );
      }
    }
    
    console.log(`📊 Citation processing summary: Found ${citationCount} clickable citations, created ${parts.length} parts`);
    
    // If no citations were found, render the entire content as markdown
    if (parts.length === 0) {
      console.log(`ℹ️ No citations found, rendering entire content as markdown`);
      return (
        <ReactMarkdown
          skipHtml={true}
          components={{
            h1: ({ children }) => (
              <h1 style={{ fontSize: '1.5em', fontWeight: 'bold', marginBottom: '0.5em' }}>
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 style={{ fontSize: '1.3em', fontWeight: 'bold', marginBottom: '0.4em' }}>
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 style={{ fontSize: '1.1em', fontWeight: 'bold', marginBottom: '0.3em' }}>
                {children}
              </h3>
            ),
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
    }
    
    return <div style={{ lineHeight: '1.5' }}>{parts}</div>;
  };

  
  try {
    return renderContentWithCitations();
  } catch (error) {
    // Fallback to plain text processing if anything fails
    console.warn('Content processing failed, falling back to plain text processing:', error);
    
    // Clean escaped newlines in fallback content
    const cleanedContent = safeContent.replace(/\\n/g, '\n');
    
    // Process citations in plain text
    const citationRegex = /\[(\d+)\]/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(cleanedContent)) !== null) {
      const citationNumber = parseInt(match[1]);
      const citation = citationMap.get(citationNumber);
      
      if (citation) {
        // Add text before citation
        if (match.index > lastIndex) {
          const textBefore = cleanedContent.substring(lastIndex, match.index);
          parts.push(
            <span key={`fallback-text-${lastIndex}`}>{textBefore}</span>
          );
        }
        
        // Add clickable citation
        parts.push(
          <CitationButton key={`fallback-citation-${citationNumber}-${match.index}`} citationNumber={citationNumber} />
        );
        
        lastIndex = match.index + match[0].length;
      }
    }
    
    // Add remaining text
    if (lastIndex < cleanedContent.length) {
      const remainingText = cleanedContent.substring(lastIndex);
      parts.push(
        <span key={`fallback-remaining-${lastIndex}`}>{remainingText}</span>
      );
    }
    
    return <div style={{ whiteSpace: 'pre-wrap' }}>{parts.length > 0 ? parts : cleanedContent}</div>;
  }
};

export default MarkdownWithCitations;
