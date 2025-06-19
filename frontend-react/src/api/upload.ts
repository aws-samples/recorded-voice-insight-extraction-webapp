// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import useHttp from '../hooks/useHttp';

// Create HTTP client instance
const httpClient = useHttp();

export interface S3PresignedRequest {
  action: string;
  username: string;
  media_file_name: string;
  use_bda?: string;
}

export interface S3PresignedResponse {
  url: string;
  fields: Record<string, string>;
}

export const uploadToS3 = async (
  file: File,
  filename: string,
  username: string,
  _authToken?: string, // Underscore prefix to indicate unused parameter (useHttp handles auth)
  useBda: boolean = false,
  onProgress?: (progress: number) => void
): Promise<boolean> => {
  const requestBody: S3PresignedRequest = {
    action: 'upload_media_file',
    username,
    media_file_name: filename,
    use_bda: useBda.toString(),
  };

  try {
    const response = await httpClient.post<S3PresignedResponse>('/s3-presigned', requestBody);
    const presignedData = response.data;

    const formData = new FormData();
    Object.entries(presignedData.fields).forEach(([key, value]) => {
      formData.append(key, value);
    });
    formData.append('file', file, filename);

    let progressInterval: number | null = null;
    let currentProgress = 0;
    
    if (onProgress) {
      onProgress(5);
      progressInterval = setInterval(() => {
        if (currentProgress < 85) {
          currentProgress += Math.random() * 10 + 5;
          if (currentProgress > 85) currentProgress = 85;
          onProgress(currentProgress);
        }
      }, 300);
    }

    try {
      const uploadResponse = await fetch(presignedData.url, {
        method: 'POST',
        body: formData,
      });

      if (progressInterval) {
        clearInterval(progressInterval);
        onProgress?.(100);
      }

      if (uploadResponse.status !== 204) {
        throw new Error(`Upload failed: ${uploadResponse.status}`);
      }

      return true;
    } catch (error) {
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      throw error;
    }
  } catch (error) {
    console.error('Error getting presigned URL:', error);
    throw new Error(`Failed to get presigned URL: ${error}`);
  }
};
