// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { Job, DDBRequest } from '../types/job';

// Use the proxy URL in development
const API_BASE_URL = '/api';

export const retrieveAllItems = async (
  username: string,
  maxRows: number | null,
  authToken: string
): Promise<Job[]> => {
  const requestBody: DDBRequest = {
    action: 'retrieve_all_items',
    username,
    max_rows: maxRows,
  };

  try {
    const response = await fetch(`${API_BASE_URL}/ddb`, {
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

    // Handle empty results
    if (!result || result.length === 0) {
      return [];
    }

    // Sort by job_creation_time in descending order (most recent first)
    const sortedJobs = result.sort((a: Job, b: Job) => {
      return new Date(b.job_creation_time).getTime() - new Date(a.job_creation_time).getTime();
    });

    return sortedJobs;
  } catch (error) {
    console.error('Error retrieving jobs:', error);
    throw error;
  }
};
