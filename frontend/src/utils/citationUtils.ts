import { Citation, PartialAnswer } from '../types/chat';

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
 * Process partial answers with their individual citations for markdown rendering
 * This creates a markdown string with citation markers that can be rendered
 * @param partialAnswers Array of partial answers from the FullQAnswer
 * @returns Object with markdown content and citation mapping
 */
export function processPartialAnswersForMarkdown(
  partialAnswers: PartialAnswer[]
): { markdownContent: string; citationMap: Map<number, ProcessedCitation> } {
  // First, collect all citations and deduplicate them
  const allCitations: Citation[] = [];
  partialAnswers.forEach(partialAnswer => {
    if (partialAnswer.citations) {
      allCitations.push(...partialAnswer.citations);
    }
  });
  
  // Create deduplicated citation list with proper IDs
  const uniqueCitations = processCitations(allCitations);
  const citationMap = new Map<number, ProcessedCitation>();
  uniqueCitations.forEach(citation => {
    citationMap.set(citation.id, citation);
  });
  
  console.log(`🔄 Processing ${partialAnswers.length} partial answers with ${uniqueCitations.length} unique citations`);

  // Now build markdown content, mapping duplicate citations to their unique IDs
  let markdownContent = '';
  
  partialAnswers.forEach((partialAnswer, answerIndex) => {
    const text = partialAnswer.partial_answer || '';
    const citations = partialAnswer.citations || [];

    console.log(`  📄 Partial answer ${answerIndex + 1}:`, {
      text: text.substring(0, 500) + (text.length > 500 ? '...' : ''),
      citationCount: citations.length,
      citations: citations.map(c => `${c.media_name}@${c.timestamp}s`)
    });

    // Add the text part (fix escaped newlines)
    if (text.trim()) {
      // Replace escaped newlines with actual newlines for proper markdown rendering
      const cleanedText = text.replace(/\\n/g, '\n');
      markdownContent += cleanedText;
    }

    // Add citations for this partial answer, mapping to unique citation IDs
    citations.forEach((citation) => {
      // Find the unique citation ID for this citation
      const uniqueCitation = uniqueCitations.find(uc => 
        uc.media_name === citation.media_name && 
        Math.abs(uc.timestamp - citation.timestamp) < 1
      );
      
      if (uniqueCitation) {
        console.log(`    📎 Adding citation [${uniqueCitation.id}]: ${citation.media_name} @ ${citation.timestamp}s`);
        markdownContent += `[${uniqueCitation.id}]`;
      }
    });

    // Add space between partial answers (except for the last one)
    if (answerIndex < partialAnswers.length - 1 && text.trim()) {
      markdownContent += ' ';
    }
  });

  console.log(`✅ Generated markdown content:`, {
    contentPreview: markdownContent.substring(0, 200) + (markdownContent.length > 200 ? '...' : ''),
    totalUniqueCitations: citationMap.size,
    citationIds: Array.from(citationMap.keys())
  });
  
  return { markdownContent, citationMap };
}

/**
 * Extract all unique citations from partial answers for the sources section
 * @param partialAnswers Array of partial answers from the FullQAnswer
 * @returns Array of processed citations with global IDs
 */
export function extractAllCitations(partialAnswers: PartialAnswer[]): ProcessedCitation[] {
  const allCitations: Citation[] = [];
  
  partialAnswers.forEach(partialAnswer => {
    if (partialAnswer.citations) {
      allCitations.push(...partialAnswer.citations);
    }
  });

  return processCitations(allCitations);
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
