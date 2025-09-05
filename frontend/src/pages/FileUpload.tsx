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
} from '@cloudscape-design/components';
import { getCurrentUser } from 'aws-amplify/auth';
import { fetchAuthSession } from 'aws-amplify/auth';
import BaseAppLayout from '../components/base-app-layout';
import { uploadToS3 } from '../api/upload';
import { checkValidFileExtension, urlEncodeFilename, getValidExtensionsString } from '../utils/fileUtils';

const FileUploadPage: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [useBda, setUseBda] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadStatus, setUploadStatus] = useState<{
    type: 'success' | 'error' | 'info' | null;
    message: string;
  }>({ type: null, message: '' });
  const [username, setUsername] = useState<string>('');
  const [authToken, setAuthToken] = useState<string>('');
  const [lastUploadedFile, setLastUploadedFile] = useState<string>('');

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
        undefined, // authToken no longer needed (useHttp handles auth)
        useBda,
        (progress) => setUploadProgress(progress)
      );
      
      if (success) {
        const analysisType = useBda ? 'Bedrock Data Automation analysis' : 'transcription';
        setUploadStatus({
          type: 'success',
          message: `${file.name} successfully uploaded and submitted for ${analysisType}. Check its progress on the Job Status page.`,
        });
        setLastUploadedFile(file.name);
        setFiles([]);
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

  return (
    <BaseAppLayout
      content={
        <ContentLayout
          header={
            <Header
              variant="h1"
              description="Upload a video or audio recording"
            >
              ReVIEW
            </Header>
          }
        >
          <SpaceBetween size="l">
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
              <Box margin={{ bottom: "l" }}>
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

            <Box>
              <SpaceBetween size="m">
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
            </Box>
          </SpaceBetween>
        </ContentLayout>
      }
    />
  );
};

export default FileUploadPage;
