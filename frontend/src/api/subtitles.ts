// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import useHttp from '../hooks/useHttp';

// Create HTTP client instance
const httpClient = useHttp();

export interface SubtitleRequest {
  username: string;
  transcript_job_id: string;
  translation_start_time?: number;
  translation_duration?: number;
  translation_destination_language?: string;
}

export class SubtitleError extends Error {
  constructor(message: string, public statusCode?: number) {
    super(message);
    this.name = 'SubtitleError';
  }
}

export class SubtitleThrottlingError extends SubtitleError {
  constructor(message: string) {
    super(message, 503);
    this.name = 'SubtitleThrottlingError';
  }
}

/**
 * Retrieve subtitles (VTT format) for a media file via job ID.
 * Optionally translate a portion of them to a new language.
 */
export const retrieveSubtitles = async (
  jobId: string,
  username: string,
  translationStartTime?: number,
  translationDuration?: number,
  translationDestinationLanguage?: string
): Promise<string> => {
  const requestBody: SubtitleRequest = {
    username,
    transcript_job_id: jobId,
  };

  // Add translation parameters if provided
  if (translationStartTime !== undefined) {
    requestBody.translation_start_time = translationStartTime;
  }
  if (translationDuration !== undefined) {
    requestBody.translation_duration = translationDuration;
  }
  if (translationDestinationLanguage) {
    requestBody.translation_destination_language = translationDestinationLanguage;
  }

  try {
    // Use the HTTP client to make the request with the correct API endpoint
    const response = await httpClient.post<string>('/subtitles', requestBody);
    
    // The API returns the VTT content as a JSON string
    if (typeof response.data === 'string') {
      return response.data;
    } else {
      throw new SubtitleError('Invalid subtitle format received from server');
    }
  } catch (error: any) {
    // Check for specific error status codes
    if (error.response) {
      if (error.response.status === 503) {
        throw new SubtitleThrottlingError(
          'Translation service is temporarily unavailable. Please try again in a few seconds.'
        );
      } else {
        throw new SubtitleError(
          `Failed to retrieve subtitles: ${error.response.status} ${error.response.statusText}`,
          error.response.status
        );
      }
    }
    
    // Handle network errors and other exceptions
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new SubtitleError('Network error: Unable to connect to subtitle service');
    }
    
    throw new SubtitleError(
      `Unexpected error retrieving subtitles: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
};
