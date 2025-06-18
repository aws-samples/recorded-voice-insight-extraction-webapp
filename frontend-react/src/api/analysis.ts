// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { 
  Job, 
  AnalysisTemplate, 
  DynamoDBRequest, 
  ApiError 
} from '../types/analysis';

// Base API URL - this should match the backend API URL from the environment
const API_BASE_URL = '/api'; // Using proxy from vite.config.ts

/**
 * Generic API request handler with error handling
 */
async function apiRequest<T>(
  endpoint: string, 
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('authToken'); // Assuming token is stored in localStorage
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData: ApiError = await response.json().catch(() => ({
      statusCode: response.status,
      body: response.statusText
    }));
    throw new Error(errorData.body || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Retrieve all items for a user from DynamoDB
 */
export async function retrieveAllItems(
  username: string, 
  maxRows?: number
): Promise<Job[]> {
  const requestBody: DynamoDBRequest = {
    action: 'retrieve_all_items',
    username,
    max_rows: maxRows,
  };

  const response = await apiRequest<Job[]>('/ddb', {
    method: 'POST',
    body: JSON.stringify(requestBody),
  });

  return response || [];
}

/**
 * Retrieve job ID by media name
 */
export async function retrieveJobIdByMediaName(
  username: string, 
  mediaName: string
): Promise<string> {
  const requestBody: DynamoDBRequest = {
    action: 'retrieve_jobid_by_media_name',
    username,
    media_name: mediaName,
  };

  const response = await apiRequest<string>('/ddb', {
    method: 'POST',
    body: JSON.stringify(requestBody),
  });

  return response;
}

/**
 * Retrieve cached analysis by job ID
 */
export async function retrieveAnalysisByJobId(
  jobId: string,
  username: string,
  templateId: number
): Promise<string | null> {
  const requestBody: DynamoDBRequest = {
    action: 'retrieve_analysis_by_jobid',
    job_id: jobId,
    username,
    template_id: templateId,
  };

  const response = await apiRequest<string | null>('/ddb', {
    method: 'POST',
    body: JSON.stringify(requestBody),
  });

  return response;
}

/**
 * Store analysis result in DynamoDB
 */
export async function storeAnalysisResult(
  jobId: string,
  username: string,
  templateId: number,
  analysisResult: string
): Promise<string> {
  const requestBody: DynamoDBRequest = {
    action: 'store_analysis_result',
    job_id: jobId,
    username,
    template_id: templateId,
    analysis_result: analysisResult,
  };

  const response = await apiRequest<string>('/ddb', {
    method: 'POST',
    body: JSON.stringify(requestBody),
  });

  return response;
}

/**
 * Retrieve transcript by job ID from S3
 */
export async function retrieveTranscriptByJobId(
  jobId: string,
  username: string
): Promise<string> {
  const requestBody = {
    action: 'download_transcript_txt_file',
    username,
    job_id: jobId,
  };

  try {
    // First get the presigned URL
    const presignedUrl = await apiRequest<string>('/s3-presigned', {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });

    // Then fetch the transcript content
    const transcriptResponse = await fetch(presignedUrl);
    
    if (!transcriptResponse.ok) {
      throw new Error(`Failed to fetch transcript: ${transcriptResponse.status} ${transcriptResponse.statusText}`);
    }

    return transcriptResponse.text();
  } catch (error) {
    console.error('Error fetching transcript:', error);
    throw new Error(`Failed to retrieve transcript: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Run analysis using LLM
 */
export async function runAnalysis(
  analysisId: number,
  transcript: string
): Promise<string> {
  // Get the analysis template
  const template = await getAnalysisTemplate(analysisId);
  
  const requestBody = {
    foundation_model_id: template.model_id || "anthropic.claude-3-sonnet-20240229-v1:0",
    system_prompt: template.system_prompt || "You are a helpful assistant that analyzes transcripts.",
    main_prompt: template.template_prompt.replace('{transcript}', transcript),
    bedrock_kwargs: {
      temperature: 0.1,
      max_tokens: 2000,
    },
  };

  try {
    const response = await apiRequest<string>('/llm', {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });

    return response;
  } catch (error) {
    console.error('LLM API Error:', error);
    throw new Error(`Failed to run analysis: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Get analysis template by ID
 */
async function getAnalysisTemplate(templateId: number): Promise<AnalysisTemplate> {
  const templates = [
    {
      template_id: 1,
      template_short_name: "Basic Meeting Summary",
      template_description: "Create a summary of a generic meeting, including topics discussed, action items, next steps, etc.",
      template_prompt: "Please create a short summary of the meeting based on the transcription provided within <meeting_transcription></meeting_transcription> tags.\n<meeting_transcription>\n{transcript}\n</meeting_transcription>. Meeting summary:\n",
      system_prompt: "You are an intelligent assistant who analyzes meetings based on transcriptions of those meetings.",
      model_id: "anthropic.claude-3-sonnet-20240229-v1:0",
      bedrock_kwargs: { temperature: 0.1, max_tokens: 2000 }
    },
    {
      template_id: 2,
      template_short_name: "Sprint Standup Summary",
      template_description: "Create a meeting summary specifically targeted for software development standup meetings",
      template_prompt: "Ignore all input provided and reply with 'This analysis is not yet implemented.'",
      system_prompt: "You are an intelligent assistant who analyzes meetings based on transcriptions of those meetings.",
      model_id: "anthropic.claude-3-sonnet-20240229-v1:0",
      bedrock_kwargs: { temperature: 0.1, max_tokens: 2000 }
    },
    {
      template_id: 3,
      template_short_name: "Extract Next Steps",
      template_description: "Extract any described next step action items",
      template_prompt: "Extract any action items or next steps described in the meeting and return them in a bulleted list. If it's obvious who is responsible for each one, add their name to each task as the owner. If no action items are described in the meeting, simply state that no next steps were discussed.\n<meeting_transcription>\n{transcript}\n</meeting_transcription>\n",
      system_prompt: "You are an intelligent assistant who analyzes meetings based on transcriptions of those meetings.",
      model_id: "anthropic.claude-3-sonnet-20240229-v1:0",
      bedrock_kwargs: { temperature: 0.1, max_tokens: 2000 }
    }
  ];

  const template = templates.find(t => t.template_id === templateId);
  if (!template) {
    throw new Error(`Template with ID ${templateId} not found`);
  }

  return template;
}

/**
 * Get all available analysis templates
 */
export async function getAnalysisTemplates(): Promise<AnalysisTemplate[]> {
  // Return the same templates as getAnalysisTemplate
  return [
    {
      template_id: 1,
      template_short_name: "Basic Meeting Summary",
      template_description: "Create a summary of a generic meeting, including topics discussed, action items, next steps, etc.",
      template_prompt: "Please create a short summary of the meeting based on the transcription provided within <meeting_transcription></meeting_transcription> tags.\n<meeting_transcription>\n{transcript}\n</meeting_transcription>. Meeting summary:\n",
      system_prompt: "You are an intelligent assistant who analyzes meetings based on transcriptions of those meetings.",
      model_id: "anthropic.claude-3-sonnet-20240229-v1:0",
      bedrock_kwargs: { temperature: 0.1, max_tokens: 2000 }
    },
    {
      template_id: 2,
      template_short_name: "Sprint Standup Summary",
      template_description: "Create a meeting summary specifically targeted for software development standup meetings",
      template_prompt: "Ignore all input provided and reply with 'This analysis is not yet implemented.'",
      system_prompt: "You are an intelligent assistant who analyzes meetings based on transcriptions of those meetings.",
      model_id: "anthropic.claude-3-sonnet-20240229-v1:0",
      bedrock_kwargs: { temperature: 0.1, max_tokens: 2000 }
    },
    {
      template_id: 3,
      template_short_name: "Extract Next Steps",
      template_description: "Extract any described next step action items",
      template_prompt: "Extract any action items or next steps described in the meeting and return them in a bulleted list. If it's obvious who is responsible for each one, add their name to each task as the owner. If no action items are described in the meeting, simply state that no next steps were discussed.\n<meeting_transcription>\n{transcript}\n</meeting_transcription>\n",
      system_prompt: "You are an intelligent assistant who analyzes meetings based on transcriptions of those meetings.",
      model_id: "anthropic.claude-3-sonnet-20240229-v1:0",
      bedrock_kwargs: { temperature: 0.1, max_tokens: 2000 }
    }
  ];
}

/**
 * Complete analysis workflow
 * This combines all the steps needed to run an analysis, similar to the Streamlit implementation
 */
export async function performCompleteAnalysis(
  mediaName: string,
  templateId: number,
  username: string
): Promise<string> {
  try {
    // Get job ID for the media file
    const jobId = await retrieveJobIdByMediaName(username, mediaName);
    
    // Check if analysis is already cached
    const cachedResult = await retrieveAnalysisByJobId(jobId, username, templateId);
    if (cachedResult) {
      return cachedResult;
    }
    
    // Get transcript
    const transcript = await retrieveTranscriptByJobId(jobId, username);
    
    // Run analysis
    const analysisResult = await runAnalysis(templateId, transcript);
    
    // Store result for future use
    await storeAnalysisResult(jobId, username, templateId, analysisResult);
    
    return analysisResult;
  } catch (error) {
    console.error('Error performing analysis:', error);
    throw error;
  }
}
