// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

export interface Job {
  UUID: string;
  media_name: string;
  job_creation_time: string;
  job_status: string;
  username: string;
  media_uri?: string;
}

export interface JobsResponse {
  items: Job[];
  error?: string;
}

export interface DDBRequest {
  action: string;
  username: string;
  max_rows?: number | null;
}
