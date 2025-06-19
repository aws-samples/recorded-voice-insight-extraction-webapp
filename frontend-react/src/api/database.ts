// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { Job } from '../types/job';
import useHttp from '../hooks/useHttp';

// Create HTTP client instance
const httpClient = useHttp();

export const retrieveAllItems = async (username: string): Promise<Job[]> => {
  const requestBody = {
    action: 'retrieve_all_items',
    username,
    max_rows: 100,
  };

  try {
    const response = await httpClient.post<Job[]>('/ddb', requestBody);
    return response.data || [];
  } catch (error) {
    console.error('Error retrieving items:', error);
    throw error;
  }
};
