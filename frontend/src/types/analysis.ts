// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Represents a job in DynamoDB with its status and metadata
 */
export interface Job {
  UUID: string;
  username: string;
  media_name: string;
  job_creation_time: string;
  job_status: JobStatus;
  media_uri?: string;
}

/**
 * Possible status values for a job
 */
export type JobStatus = 
  | "Transcribing"
  | "Indexing"
  | "Transcription Complete"
  | "Completed"
  | "Failed"
  | "In Transcription Queue"
  | "BDA Analysis Complete";

/**
 * Represents an analysis template
 */
export interface AnalysisTemplate {
  template_id: string;
  template_short_name: string;
  template_description: string;
  template_prompt: string;
  system_prompt?: string;
  model_id?: string;
  user_id?: string;
  bedrock_kwargs?: {
    temperature: number;
    maxTokens: number;
    topP?: number;
    topK?: number;
    stopSequences?: string[];
  };
}

/**
 * Request payload for running analysis
 */
export interface AnalysisRequest {
  foundation_model_id: string;
  system_prompt: string;
  main_prompt: string;
  bedrock_kwargs: {
    temperature: number;
    maxTokens: number; 
    topP?: number;
    topK?: number;
    stopSequences?: string[];
  };
}

/**
 * Response from analysis API
 */
export interface AnalysisResponse {
  statusCode: number;
  body: string;
}

/**
 * Props for the AnalysisResults component
 */
export interface AnalysisResultsProps {
  result: string;
  isLoading: boolean;
  error?: string;
}

/**
 * API error response
 */
export interface ApiError {
  statusCode: number;
  body: string;
}

/**
 * State for the analysis page
 */
export interface AnalysisPageState {
  selectedMediaName: string | null;
  selectedAnalysisTemplate: string | null;
  analysisResult: string | null;
  isLoading: boolean;
  error: string | null;
  completedJobs: Job[];
  analysisTemplates: AnalysisTemplate[];
}

/**
 * DynamoDB operations for analysis
 */
export interface DynamoDBRequest {
  action: string;
  username: string;
  maxRows?: number;
  jobId?: string;
  templateId?: number;
  analysisResult?: string;
  mediaName?: string;
}

/**
 * Response from DynamoDB operations
 */
export type DynamoDBResponse = Job[] | string | null;
