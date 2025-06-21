// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import useHttp from '../hooks/useHttp';

/**
 * Functions for interacting with S3 via API Gateway
 */

// Create HTTP client instance
const httpClient = useHttp();

/**
 * Get a presigned URL for a media file
 * @param mediaName The name of the media file
 * @param username The current user's username
 * @param authToken The authentication token (not needed as useHttp handles auth)
 * @returns Promise resolving to the presigned URL
 */
export async function getMediaPresignedUrl(
  mediaName: string,
  username: string,
  _authToken?: string // Underscore prefix to indicate unused parameter
): Promise<string> {
  console.log(`🔗 Requesting presigned URL for: ${mediaName}`);
  
  const requestBody = {
    action: 'download_media_file',
    media_file_name: mediaName,
    username: username
  };

  try {
    const response = await httpClient.post<string>('/s3-presigned', requestBody);
    console.log(`✅ Received presigned URL response:`, response.data);
    
    // Ensure we return a valid string URL
    if (typeof response.data === 'string' && response.data.trim() !== '') {
      return response.data;
    } else {
      throw new Error('Invalid presigned URL received from server');
    }
  } catch (error) {
    console.error(`❌ Presigned URL request failed:`, error);
    throw new Error(`Failed to get presigned URL: ${error}`);
  }
}
