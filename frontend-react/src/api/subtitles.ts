// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

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
  idToken: string,
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
    const response = await fetch('/api/subtitles', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': idToken,
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      if (response.status === 503) {
        throw new SubtitleThrottlingError(
          'Translation service is temporarily unavailable. Please try again in a few seconds.'
        );
      } else {
        const errorText = await response.text();
        throw new SubtitleError(
          `Failed to retrieve subtitles: ${response.status} ${response.statusText}. ${errorText}`,
          response.status
        );
      }
    }

    const subtitleContent = await response.json();
    
    // The API returns the VTT content as a JSON string
    if (typeof subtitleContent === 'string') {
      return subtitleContent;
    } else {
      throw new SubtitleError('Invalid subtitle format received from server');
    }

  } catch (error) {
    if (error instanceof SubtitleError) {
      throw error;
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
