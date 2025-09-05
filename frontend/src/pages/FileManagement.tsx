// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React, { useState, useEffect } from 'react';
import {
  ContentLayout,
  Header,
  SpaceBetween,
  FileUpload as CloudscapeFileUpload,
  FileUploadProps,
  Checkbox,
  Alert,
  Box,
  Button,
  Grid,
  Container,
  Multiselect,
  MultiselectProps,
} from '@cloudscape-design/components';
import { getCurrentUser } from 'aws-amplify/auth';
import { fetchAuthSession } from 'aws-amplify/auth';
import BaseAppLayout from '../components/base-app-layout';
import JobStatusTable from '../components/JobStatusTable';
import { uploadToS3 } from '../api/upload';
import { deleteFileByJobId } from '../api/fileManagement';
import { useAnalysisApi } from '../hooks/useAnalysisApi';
import { checkValidFileExtension, urlEncodeFilename, urlDecodeFilename, getValidExtensionsString } from '../utils/fileUtils';
import { Job } from '../types/job';

const FileManagementPage: React.FC = () => {
  // File Upload State
  const [files, setFiles] = useState<File[]>([]);
  const [useBda, setUseBda] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadStatus, setUploadStatus] = useState<{
    type: 'success' | 'error' | 'info' | null;
    message: string;
  }>({ type: null, message: '' });
  const [lastUploadedFile, setLastUploadedFile] = useState<string>('');

  // Job Status State
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isManualRefresh, setIsManualRefresh] = useState<boolean>(false);
  const { loading: jobsLoading, error: jobsError, retrieveAllItems: fetchJobsData, clearError } = useAnalysisApi();

  // File Management State
  const [selectedFiles, setSelectedFiles] = useState<MultiselectProps.Option[]>([]);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [fileManagementAlert, setFileManagementAlert] = useState<{
    type: 'success' | 'error' | 'info' | null;
    message: string;
  }>({ type: null, message: '' });

  // Authentication State
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
          setUploadStatus({
            type: 'error',
            message: 'Authentication required. Please log in.',
          });
        }
      } catch (err) {
        console.error('Authentication error:', err);
        setUploadStatus({
          type: 'error',
          message: 'Authentication failed. Please log in.',
        });
      }
    };

    initAuth();
  }, []);

  // Fetch jobs data
  const fetchJobs = async (isManual: boolean = false) => {
    if (!username) {
      return;
    }

    if (isManual) {
      setIsManualRefresh(true);
    }

    clearError();

    try {
      const jobsData = await fetchJobsData(username, 100);
      setJobs(jobsData);
    } catch (err) {
      console.error('Error fetching jobs:', err);
    } finally {
      if (isManual) {
        setIsManualRefresh(false);
      }
    }
  };

  // Fetch jobs when authentication is ready
  useEffect(() => {
    if (username) {
      fetchJobs();
    }
  }, [username]);

  // Auto-refresh jobs table every 10 seconds
  useEffect(() => {
    if (!username) return;

    const interval = setInterval(() => {
      // Only refresh if not currently loading to avoid overlapping requests
      if (!jobsLoading && !isManualRefresh) {
        fetchJobs(false); // false = automatic refresh, no loading indicator
      }
    }, 10000); // 10 seconds

    // Cleanup interval on component unmount or when username changes
    return () => clearInterval(interval);
  }, [username]); // Remove jobsLoading and isManualRefresh from dependencies

  // File Upload Handlers
  const handleFileChange: FileUploadProps['onChange'] = ({ detail }) => {
    setFiles(detail.value);
    setUploadStatus({ type: null, message: '' });
    setUploadProgress(0);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setUploadStatus({
        type: 'error',
        message: 'Please select a file to upload.',
      });
      return;
    }

    if (!username || !authToken) {
      setUploadStatus({
        type: 'error',
        message: 'Authentication required. Please refresh the page and log in.',
      });
      return;
    }

    const file = files[0];
    
    if (lastUploadedFile === file.name) {
      return;
    }

    if (!checkValidFileExtension(file.name)) {
      setUploadStatus({
        type: 'error',
        message: `Invalid file extension. Allowed extensions are: ${getValidExtensionsString()}.`,
      });
      return;
    }

    const urlEncodedFilename = urlEncodeFilename(file.name);

    setUploading(true);
    setUploadProgress(0);
    setUploadStatus({
      type: 'info',
      message: `Uploading file ${file.name}...`,
    });

    try {
      const success = await uploadToS3(
        file, 
        urlEncodedFilename, 
        username, 
        undefined,
        useBda,
        (progress) => setUploadProgress(progress)
      );
      
      if (success) {
        const analysisType = useBda ? 'Bedrock Data Automation analysis' : 'transcription';
        setUploadStatus({
          type: 'success',
          message: `${file.name} successfully uploaded and submitted for ${analysisType}.`,
        });
        setLastUploadedFile(file.name);
        setFiles([]);
        
        // Refresh jobs table after successful upload
        // Wait a bit longer for backend to process and create DDB entry
        setTimeout(() => {
          fetchJobs(false);
        }, 2000); // 2 seconds instead of immediate + 1 second
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadStatus({
        type: 'error',
        message: error instanceof Error ? error.message : 'Upload failed. Please try again.',
      });
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  // Job Status Handlers
  const handleRefreshJobs = () => {
    fetchJobs(true); // true = manual refresh, show loading indicator
  };

  // File Management Handlers
  const fileOptions: MultiselectProps.Option[] = jobs
    .map(job => ({
      label: urlDecodeFilename(job.media_name),
      value: job.media_name,
      description: `Status: ${job.job_status} | Created: ${job.job_creation_time}`,
    }))
    .sort((a, b) => a.label.localeCompare(b.label));

  const handleSelectionChange = ({ detail }: any) => {
    setSelectedFiles(detail.selectedOptions);
  };

  const handleDelete = async () => {
    if (selectedFiles.length === 0) {
      setFileManagementAlert({
        type: 'error',
        message: 'Please select files to delete.',
      });
      return;
    }

    if (!username || !authToken) {
      setFileManagementAlert({
        type: 'error',
        message: 'Authentication required. Please refresh the page and log in.',
      });
      return;
    }

    setDeleting(true);
    setFileManagementAlert({ type: null, message: '' });

    try {
      for (const selectedFile of selectedFiles) {
        const mediaName = selectedFile.value as string;
        const job = jobs.find(j => j.media_name === mediaName);
        
        if (job) {
          const decodedName = urlDecodeFilename(mediaName);
          setFileManagementAlert({
            type: 'info',
            message: `Deleting ${decodedName}...`,
          });
          
          await deleteFileByJobId(job.UUID, username);
        }
      }

      setFileManagementAlert({
        type: 'success',
        message: 'File deletion complete.',
      });

      setSelectedFiles([]);
      await fetchJobs(false);

    } catch (error) {
      console.error('Delete failed:', error);
      setFileManagementAlert({
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
              description="Upload, monitor, and manage your media files"
            >
              File Management
            </Header>
          }
        >
          <SpaceBetween size="l">
            <Grid
              gridDefinition={[
                { colspan: { default: 12, xs: 6 } }, // File Upload - Upper Left
                { colspan: { default: 12, xs: 6 } }, // File Management - Upper Right
                { colspan: 12 } // Job Status - Full Width Below
              ]}
            >
              {/* File Upload Block - Upper Left */}
              <Container
                header={
                  <Header
                    variant="h2"
                    description="Upload a video or audio recording"
                  >
                    File Upload
                  </Header>
                }
              >
                <SpaceBetween size="m">
                  {uploadStatus.type && (
                    <Alert
                      type={uploadStatus.type}
                      dismissible
                      onDismiss={() => setUploadStatus({ type: null, message: '' })}
                    >
                      {uploadStatus.message}
                    </Alert>
                  )}

                  {uploading && (
                    <Box margin={{ bottom: "m" }}>
                      <div style={{ padding: "16px", border: "1px solid #ddd", borderRadius: "8px" }}>
                        <div style={{ marginBottom: "8px", fontWeight: "bold" }}>
                          Upload Progress: {Math.round(uploadProgress)}%
                        </div>
                        <div style={{ 
                          width: "100%", 
                          height: "8px", 
                          backgroundColor: "#e0e0e0", 
                          borderRadius: "4px",
                          overflow: "hidden"
                        }}>
                          <div style={{
                            width: `${uploadProgress}%`,
                            height: "100%",
                            backgroundColor: "#0073bb",
                            transition: "width 0.3s ease"
                          }} />
                        </div>
                      </div>
                    </Box>
                  )}

                  <CloudscapeFileUpload
                    onChange={handleFileChange}
                    value={files}
                    i18nStrings={{
                      uploadButtonText: (e) => (e ? 'Choose files' : 'Choose file'),
                      dropzoneText: (e) =>
                        e ? 'Drop files to upload' : 'Drop file to upload',
                      removeFileAriaLabel: (e) => `Remove file ${e + 1}`,
                      limitShowFewer: 'Show fewer files',
                      limitShowMore: 'Show more files',
                      errorIconAriaLabel: 'Error',
                    }}
                    multiple={false}
                    accept={`.${getValidExtensionsString().split(', ').join(',.')}`}
                    showFileLastModified
                    showFileSize
                    showFileThumbnail
                    constraintText={`Supported formats: ${getValidExtensionsString()}`}
                  />

                  <Checkbox
                    onChange={({ detail }) => setUseBda(detail.checked)}
                    checked={useBda}
                  >
                    Analyze file with Bedrock Data Automation
                  </Checkbox>

                  <Button
                    variant="primary"
                    onClick={handleUpload}
                    loading={uploading}
                    disabled={files.length === 0 || !username || !authToken}
                  >
                    Upload File
                  </Button>
                </SpaceBetween>
              </Container>

              {/* File Management Block - Upper Right */}
              <Container
                header={
                  <Header
                    variant="h2"
                    description="Remove uploaded files"
                  >
                    File Deletion
                  </Header>
                }
              >
                <SpaceBetween size="m">
                  {fileManagementAlert.type && (
                    <Alert
                      type={fileManagementAlert.type}
                      dismissible
                      onDismiss={() => setFileManagementAlert({ type: null, message: '' })}
                    >
                      {fileManagementAlert.message}
                    </Alert>
                  )}

                  <Multiselect
                    selectedOptions={selectedFiles}
                    onChange={handleSelectionChange}
                    options={fileOptions}
                    placeholder="Select file(s) to permanently delete"
                    empty="No files available"
                    loadingText="Loading files..."
                    statusType={jobsLoading ? "loading" : "finished"}
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
              </Container>

              {/* Job Status Block - Full Width Below */}
              <Container>
                <JobStatusTable
                  jobs={jobs}
                  loading={jobsLoading && isManualRefresh}
                  error={jobsError}
                  onRefresh={handleRefreshJobs}
                />
              </Container>
            </Grid>
          </SpaceBetween>
        </ContentLayout>
      }
    />
  );
};

export default FileManagementPage;
