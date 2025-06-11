import { Citation } from '../types/chat';

export interface ProcessedCitation extends Citation {
  id: number;
  displayText: string;
}

/**
 * Process citations from a FullQAnswer and create numbered citation references
 * @param citations Array of citations from the response
 * @returns Array of processed citations with unique IDs and display text
 */
export function processCitations(citations: Citation[]): ProcessedCitation[] {
  // Remove duplicates based on media_name and timestamp
  const uniqueCitations = citations.filter((citation, index, self) => 
    index === self.findIndex(c => 
      c.media_name === citation.media_name && 
      Math.abs(c.timestamp - citation.timestamp) < 1 // Within 1 second tolerance
    )
  );

  // Add sequential IDs and display text
  return uniqueCitations.map((citation, index) => ({
    ...citation,
    id: index + 1,
    displayText: `[${index + 1}]`
  }));
}

/**
 * Parse text and identify citation markers
 * @param text The text content to process
 * @param citations Array of processed citations
 * @returns Array of text parts and citation references
 */
export function parseCitationText(
  text: string, 
  citations: ProcessedCitation[]
): Array<{ type: 'text' | 'citation'; content: string; citation?: ProcessedCitation }> {
  if (!citations.length) {
    return [{ type: 'text', content: text }];
  }

  const parts: Array<{ type: 'text' | 'citation'; content: string; citation?: ProcessedCitation }> = [];
  let lastIndex = 0;
  
  // Look for citation patterns in the text (e.g., [1], [2])
  const citationRegex = /\[(\d+)\]/g;
  let match;
  
  while ((match = citationRegex.exec(text)) !== null) {
    const citationNumber = parseInt(match[1]);
    const citation = citations.find(c => c.id === citationNumber);
    
    if (citation) {
      // Add text before citation
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: text.substring(lastIndex, match.index)
        });
      }
      
      // Add citation reference
      parts.push({
        type: 'citation',
        content: citation.displayText,
        citation: citation
      });
      
      lastIndex = match.index + match[0].length;
    }
  }
  
  // Add remaining text
  if (lastIndex < text.length) {
    parts.push({
      type: 'text',
      content: text.substring(lastIndex)
    });
  }
  
  return parts.length > 0 ? parts : [{ type: 'text', content: text }];
}

/**
 * Format timestamp in seconds to MM:SS or HH:MM:SS format
 * @param seconds Timestamp in seconds
 * @returns Formatted time string
 */
export function formatTimestamp(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  } else {
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }
}
