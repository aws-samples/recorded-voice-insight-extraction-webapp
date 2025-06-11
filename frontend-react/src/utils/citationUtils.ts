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
 * Insert citation markers at the end of sentences or logical breaks in the text
 * This approach adds citations at the end since the backend doesn't provide specific insertion points
 * @param text The text content to process
 * @param citations Array of processed citations
 * @returns Array of text parts and citation references
 */
export function insertCitationMarkers(
  text: string, 
  citations: ProcessedCitation[]
): Array<{ type: 'text' | 'citation'; content: string; citation?: ProcessedCitation }> {
  if (!citations.length) {
    return [{ type: 'text', content: text }];
  }

  // For now, we'll add all citations at the end of the text
  // This is a simple approach that works when the backend doesn't specify insertion points
  const parts: Array<{ type: 'text' | 'citation'; content: string; citation?: ProcessedCitation }> = [];
  
  // Add the main text
  parts.push({ type: 'text', content: text });
  
  // Add each citation marker
  citations.forEach((citation, index) => {
    if (index === 0) {
      parts.push({ type: 'text', content: ' ' }); // Add space before first citation
    }
    parts.push({
      type: 'citation',
      content: citation.displayText,
      citation: citation
    });
  });

  return parts;
}

/**
 * Alternative approach: Insert citations at sentence boundaries
 * This distributes citations throughout the text more naturally
 */
export function insertCitationsAtSentences(
  text: string,
  citations: ProcessedCitation[]
): Array<{ type: 'text' | 'citation'; content: string; citation?: ProcessedCitation }> {
  if (!citations.length) {
    return [{ type: 'text', content: text }];
  }

  const parts: Array<{ type: 'text' | 'citation'; content: string; citation?: ProcessedCitation }> = [];
  
  // Split text into sentences (simple approach)
  const sentences = text.split(/([.!?]+\s+)/).filter(s => s.trim().length > 0);
  
  if (sentences.length <= 1) {
    // If no clear sentence breaks, add citations at the end
    return insertCitationMarkers(text, citations);
  }

  // Distribute citations across sentences
  const citationsPerSentence = Math.ceil(citations.length / Math.max(1, sentences.length - 1));
  let citationIndex = 0;

  sentences.forEach((sentence, index) => {
    parts.push({ type: 'text', content: sentence });
    
    // Add citations after some sentences (not the last one)
    if (index < sentences.length - 1 && citationIndex < citations.length) {
      const citationsToAdd = Math.min(citationsPerSentence, citations.length - citationIndex);
      
      for (let i = 0; i < citationsToAdd; i++) {
        if (citationIndex < citations.length) {
          parts.push({
            type: 'citation',
            content: citations[citationIndex].displayText,
            citation: citations[citationIndex]
          });
          citationIndex++;
        }
      }
    }
  });

  // Add any remaining citations at the end
  while (citationIndex < citations.length) {
    parts.push({
      type: 'citation',
      content: citations[citationIndex].displayText,
      citation: citations[citationIndex]
    });
    citationIndex++;
  }

  return parts;
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
