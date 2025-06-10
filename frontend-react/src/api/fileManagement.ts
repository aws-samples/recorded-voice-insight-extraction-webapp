// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// Use the proxy URL in development
const API_BASE_URL = '/api';

export const deleteFileByJobId = async (
  jobId: string,
  username: string,
  authToken: string
): Promise<string> => {
  const requestBody = {
    username,
    job_id: jobId,
  };

  try {
    const response = await fetch(`${API_BASE_URL}/kb-job-deletion`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authToken,
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error('Error deleting file:', error);
    throw error;
  }
};
