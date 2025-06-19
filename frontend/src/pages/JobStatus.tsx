// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React, { useState, useEffect } from 'react';
import { ContentLayout } from '@cloudscape-design/components';
import { getCurrentUser } from 'aws-amplify/auth';
import JobStatusTable from '../components/JobStatusTable';
import { useAnalysisApi } from '../hooks/useAnalysisApi';
import { Job } from '../types/job';
import BaseAppLayout from '../components/base-app-layout';

const JobStatus: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [username, setUsername] = useState<string>('');
  const { loading, error, retrieveAllItems, clearError } = useAnalysisApi();

  // Initialize authentication
  useEffect(() => {
    const initAuth = async () => {
      try {
        const user = await getCurrentUser();
        
        if (user.username) {
          setUsername(user.username);
        }
      } catch (err) {
        console.error('Authentication error:', err);
      }
    };

    initAuth();
  }, []);

  // Fetch jobs data
  const fetchJobs = async () => {
    if (!username) {
      return;
    }

    clearError();

    try {
      const jobsData = await retrieveAllItems(username, 100);
      setJobs(jobsData);
    } catch (err) {
      console.error('Error fetching jobs:', err);
      // Error is handled by the hook
    }
  };

  // Fetch jobs when authentication is ready
  useEffect(() => {
    if (username) {
      fetchJobs();
    }
  }, [username]);

  // Handle refresh button click
  const handleRefresh = () => {
    fetchJobs();
  };

  return (
    <BaseAppLayout
      content={
        <ContentLayout>
          <JobStatusTable
            jobs={jobs}
            loading={loading}
            error={error}
            onRefresh={handleRefresh}
          />
        </ContentLayout>
      }
    />
  );
};

export default JobStatus;
