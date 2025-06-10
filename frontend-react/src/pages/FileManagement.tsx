// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React, { useState, useEffect } from 'react';
import {
  ContentLayout,
  Header,
  SpaceBetween,
  Multiselect,
  MultiselectProps,
  Button,
  Alert,
  Box,
} from '@cloudscape-design/components';
import { getCurrentUser } from 'aws-amplify/auth';
import { fetchAuthSession } from 'aws-amplify/auth';
import BaseAppLayout from '../components/base-app-layout';
import { retrieveAllItems } from '../api/db';
import { deleteFileByJobId } from '../api/fileManagement';
import { Job } from '../types/job';

const FileManagementPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<MultiselectProps.Option[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [username, setUsername] = useState<string>('');
  const [authToken, setAuthToken] = useState<string>('');
  const [alert, setAlert] = useState<{
    type: 'success' | 'error' | 'info' | null;
    message: string;
  }>({ type: null, message: '' });

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
          setAlert({
            type: 'error',
            message: 'Authentication required. Please log in.',
          });
        }
      } catch (err) {
        console.error('Authentication error:', err);
        setAlert({
          type: 'error',
          message: 'Authentication failed. Please log in.',
        });
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
    setAlert({ type: null, message: '' });

    try {
      const jobsData = await retrieveAllItems(username, null, authToken);
      setJobs(jobsData);
    } catch (err) {
      console.error('Error fetching jobs:', err);
      setAlert({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to load files',
      });
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

  // Convert jobs to multiselect options, sorted alphabetically
  const fileOptions: MultiselectProps.Option[] = jobs
    .map(job => ({
      label: job.media_name,
      value: job.media_name,
      description: `Status: ${job.job_status} | Created: ${job.job_creation_time}`,
    }))
    .sort((a, b) => a.label.localeCompare(b.label));

  // Handle file selection change
  const handleSelectionChange = ({ detail }: { detail: MultiselectProps.ChangeDetail }) => {
    setSelectedFiles(detail.selectedOptions);
  };

  // Handle delete button click
  const handleDelete = async () => {
    if (selectedFiles.length === 0) {
      setAlert({
        type: 'error',
        message: 'Please select files to delete.',
      });
      return;
    }

    if (!username || !authToken) {
      setAlert({
        type: 'error',
        message: 'Authentication required. Please refresh the page and log in.',
      });
      return;
    }

    setDeleting(true);
    setAlert({ type: null, message: '' });

    try {
      // Delete files sequentially (matching Streamlit behavior)
      for (const selectedFile of selectedFiles) {
        const mediaName = selectedFile.value as string;
        const job = jobs.find(j => j.media_name === mediaName);
        
        if (job) {
          setAlert({
            type: 'info',
            message: `Deleting ${mediaName}...`,
          });
          
          await deleteFileByJobId(job.UUID, username, authToken);
        }
      }

      setAlert({
        type: 'success',
        message: 'File deletion complete.',
      });

      // Clear selection and refresh the file list
      setSelectedFiles([]);
      await fetchJobs();

    } catch (error) {
      console.error('Delete failed:', error);
      setAlert({
        type: 'error',
        message: error instanceof Error ? error.message : 'Delete failed. Please try again.',
      });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <BaseAppLayout
      content={
        <ContentLayout
          header={
            <Header
              variant="h1"
              description="Manage uploaded files"
            >
              File Management
            </Header>
          }
        >
          <SpaceBetween size="l">
            {alert.type && (
              <Alert
                type={alert.type}
                dismissible
                onDismiss={() => setAlert({ type: null, message: '' })}
              >
                {alert.message}
              </Alert>
            )}

            <Box>
              <SpaceBetween size="m">
                <Header variant="h3">
                  Choose files to delete:
                </Header>

                <Multiselect
                  selectedOptions={selectedFiles}
                  onChange={handleSelectionChange}
                  options={fileOptions}
                  placeholder="Select file(s) to permanently delete"
                  empty="No files available"
                  loadingText="Loading files..."
                  statusType={loading ? "loading" : "finished"}
                  filteringType="auto"
                />

                <Button
                  variant="primary"
                  onClick={handleDelete}
                  loading={deleting}
                  disabled={selectedFiles.length === 0 || !username || !authToken}
                >
                  Delete Permanently
                </Button>
              </SpaceBetween>
            </Box>
          </SpaceBetween>
        </ContentLayout>
      }
    />
  );
};

export default FileManagementPage;
