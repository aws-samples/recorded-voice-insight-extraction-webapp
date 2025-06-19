// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import useHttp from '../hooks/useHttp';

// Create HTTP client instance
const httpClient = useHttp();

export const deleteFileByJobId = async (
  jobId: string,
  username: string,
  _authToken?: string // Underscore prefix to indicate unused parameter (useHttp handles auth)
): Promise<string> => {
  const requestBody = {
    username,
    job_id: jobId,
  };

  try {
    const response = await httpClient.post<string>('/kb-job-deletion', requestBody);
    return response.data;
  } catch (error) {
    console.error('Error deleting file:', error);
    throw error;
  }
};
