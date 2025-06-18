// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React, { useState, useEffect } from 'react';
import { ContentLayout } from '@cloudscape-design/components';
import { getCurrentUser } from 'aws-amplify/auth';
import { fetchAuthSession } from 'aws-amplify/auth';
import JobStatusTable from '../components/JobStatusTable';
import { retrieveAllItems } from '../api/db';
import { Job } from '../types/job';
import BaseAppLayout from '../components/base-app-layout';

const JobStatus: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [username, setUsername] = useState<string>('');
  const [authToken, setAuthToken] = useState<string>('');

  // Initialize authentication
  useEffect(() => {
    const initAuth = async () => {
      try {
        const user = await getCurrentUser();
        const session = await fetchAuthSession();
        
        if (user.username && session.tokens?.idToken) {
          setUsername(user.username);
          setAuthToken(`Bearer ${session.tokens.idToken.toString()}`);
        } else {
          setError('Authentication required. Please log in.');
        }
      } catch (err) {
        console.error('Authentication error:', err);
        setError('Authentication failed. Please log in.');
      }
    };

    initAuth();
  }, []);

  // Fetch jobs data
  const fetchJobs = async () => {
    if (!username || !authToken) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const jobsData = await retrieveAllItems(username, null, authToken);
      setJobs(jobsData);
    } catch (err) {
      console.error('Error fetching jobs:', err);
      setError(err instanceof Error ? err.message : 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  // Fetch jobs when authentication is ready
  useEffect(() => {
    if (username && authToken) {
      fetchJobs();
    }
  }, [username, authToken]);

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
