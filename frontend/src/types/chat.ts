export interface JobData {
  media_name: string;
  job_creation_time: string;
  job_status: string;
  UUID: string;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: Array<{ text: string }>;
  full_answer?: FullQAnswer;
}

export interface Citation {
  media_name: string;
  timestamp: number;
}

export interface PartialAnswer {
  partial_answer: string;
  citations: Citation[];
}

export interface FullQAnswer {
  answer: PartialAnswer[];
}
