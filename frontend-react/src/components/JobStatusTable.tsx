// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React from 'react';
import {
  Table,
  Box,
  SpaceBetween,
  Button,
  Header,
  Spinner,
  Alert,
} from '@cloudscape-design/components';
import { Job } from '../types/job';

interface JobStatusTableProps {
  jobs: Job[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

const JobStatusTable: React.FC<JobStatusTableProps> = ({
  jobs,
  loading,
  error,
  onRefresh,
}) => {
  const getStatusColor = (status: string): string => {
    if (status === 'Completed' || status === 'BDA Analysis Complete') {
      return 'text-status-success';
    }
    if (status === 'Failed') {
      return 'text-status-error';
    }
    if (status?.includes('Queue') || status?.includes('Transcribing') || status?.includes('Indexing')) {
      return 'text-status-info';
    }
    return 'text-body-default';
  };

  const columnDefinitions = [
    {
      id: 'media_name',
      header: 'Media Name',
      cell: (item: Job) => item.media_name || '-',
      sortingField: 'media_name',
    },
    {
      id: 'job_creation_time',
      header: 'Job Creation Time',
      cell: (item: Job) => {
        if (!item.job_creation_time) return '-';
        try {
          const date = new Date(item.job_creation_time);
          return date.toLocaleString();
        } catch {
          return item.job_creation_time;
        }
      },
      sortingField: 'job_creation_time',
    },
    {
      id: 'job_status',
      header: 'Job Status',
      cell: (item: Job) => (
        <Box color={getStatusColor(item.job_status)}>
          {item.job_status || 'Unknown'}
        </Box>
      ),
      sortingField: 'job_status',
    },
  ];

  if (error) {
    return (
      <SpaceBetween size="l">
        <Header
          variant="h1"
          actions={
            <Button onClick={onRefresh} loading={loading}>
              Refresh Table
            </Button>
          }
        >
          Job Status
        </Header>
        <Alert type="error" header="Error loading jobs">
          {error}
        </Alert>
      </SpaceBetween>
    );
  }

  return (
    <SpaceBetween size="l">
      <Header
        variant="h1"
        description="Check Transcription Job Status"
        actions={
          <Button onClick={onRefresh} loading={loading}>
            Refresh Table
          </Button>
        }
      >
        Job Status
      </Header>

      {loading && jobs.length === 0 ? (
        <Box textAlign="center" padding="l">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary">
            Loading jobs...
          </Box>
        </Box>
      ) : (
        <Table
          columnDefinitions={columnDefinitions}
          items={jobs}
          loading={loading}
          loadingText="Refreshing jobs..."
          sortingDisabled={false}
          empty={
            <Box textAlign="center" color="inherit">
              <Box variant="strong" textAlign="center" color="inherit">
                No jobs found
              </Box>
              <Box variant="p" padding={{ bottom: 's' }} color="inherit">
                Upload a media file to see transcription jobs here.
              </Box>
            </Box>
          }
          header={
            <Header
              counter={jobs.length > 0 ? `(${jobs.length})` : ''}
            >
              Transcription Jobs
            </Header>
          }
        />
      )}
    </SpaceBetween>
  );
};

export default JobStatusTable;
