// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { Job, DDBRequest } from '../types/job';
import useHttp from '../hooks/useHttp';

// Create HTTP client instance
const httpClient = useHttp();

export const retrieveAllItems = async (
  username: string,
  maxRows: number | null,
  _authToken?: string // Underscore prefix to indicate unused parameter
): Promise<Job[]> => {
  const requestBody: DDBRequest = {
    action: 'retrieve_all_items',
    username,
    max_rows: maxRows,
  };

  try {
    const response = await httpClient.post<Job[]>('/ddb', requestBody);
    const result = response.data;

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
