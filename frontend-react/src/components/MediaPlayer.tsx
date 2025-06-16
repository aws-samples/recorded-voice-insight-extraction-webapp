// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React, { useRef, useEffect, useState } from 'react';
import {
  Modal,
  Box,
  Button,
  SpaceBetween,
  Alert,
  Spinner
} from '@cloudscape-design/components';
import { ProcessedCitation } from '../utils/citationUtils';
import { retrieveSubtitles, SubtitleThrottlingError, SubtitleError } from '../api/subtitles';
import { SupportedLanguage } from '../constants/languages';
import { JobData } from '../types/chat';

interface MediaPlayerProps {
  citation: ProcessedCitation | null;
  isVisible: boolean;
  onClose: () => void;
  onGetPresignedUrl: (mediaName: string) => Promise<string>;
  displaySubtitles?: boolean;
  translationLanguage?: SupportedLanguage;
  username?: string;
  idToken?: string;
  jobData?: JobData[];
}

const MediaPlayer: React.FC<MediaPlayerProps> = ({
  citation,
  isVisible,
  onClose,
  onGetPresignedUrl,
  displaySubtitles = false,
  translationLanguage,
  username,
  idToken,
  jobData = []
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [mediaUrl, setMediaUrl] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [mediaType, setMediaType] = useState<'video' | 'audio'>('video');
  const [subtitleUrl, setSubtitleUrl] = useState<string>('');
  const [isLoadingSubtitles, setIsLoadingSubtitles] = useState<boolean>(false);
  const [subtitleError, setSubtitleError] = useState<string>('');
  const [isTranslating, setIsTranslating] = useState<boolean>(false);

  const loadMedia = async () => {
    if (!citation) return;

    setIsLoading(true);
    setError('');
    
    try {
      console.log(`🎬 Loading media: ${citation.media_name} at ${citation.timestamp}s`);
      
      // Get presigned URL for the media file
      const url = await onGetPresignedUrl(citation.media_name);
      console.log(`🔗 Received presigned URL: ${url.substring(0, 100)}...`);
      
      setMediaUrl(url);
      
      // Determine media type based on file extension
      const extension = citation.media_name.toLowerCase().split('.').pop();
      const videoExtensions = ['mp4', 'webm', 'ogg', 'mov', 'avi'];
      const audioExtensions = ['mp3', 'wav', 'ogg', 'm4a', 'aac'];
      
      if (videoExtensions.includes(extension || '')) {
        setMediaType('video');
        console.log(`📹 Detected video file: ${extension}`);
      } else if (audioExtensions.includes(extension || '')) {
        setMediaType('audio');
        console.log(`🎵 Detected audio file: ${extension}`);
      } else {
        setMediaType('video'); // Default to video
        console.log(`❓ Unknown file type: ${extension}, defaulting to video`);
      }
      
    } catch (err) {
      console.error('❌ Error loading media:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load media';
      setError(`Failed to load media: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSubtitles = async () => {
    if (!citation || !username || !idToken) return;

    setIsLoadingSubtitles(true);
    setSubtitleError('');
    setIsTranslating(!!translationLanguage);
    
    try {
      // Find the job ID for this media file
      const job = jobData.find(j => j.media_name === citation.media_name);
      if (!job) {
        throw new Error(`Could not find job data for media: ${citation.media_name}`);
      }

      console.log(`🎬 Loading subtitles for: ${citation.media_name} (Job ID: ${job.UUID})`);
      
      let translationStartTime: number | undefined;
      let translationDuration: number | undefined;
      let translationDestinationLanguage: string | undefined;

      // If translation is requested, set parameters
      if (translationLanguage) {
        translationStartTime = citation.timestamp;
        translationDuration = 60; // seconds - translate 1 minute around the citation
        translationDestinationLanguage = translationLanguage;
        console.log(`🌐 Translating subtitles to ${translationLanguage} from ${translationStartTime}s for ${translationDuration}s`);
      }

      const vttContent = await retrieveSubtitles(
        job.UUID,
        username,
        idToken,
        translationStartTime,
        translationDuration,
        translationDestinationLanguage
      );

      // Create a blob URL for the VTT content
      const blob = new Blob([vttContent], { type: 'text/vtt' });
      const url = URL.createObjectURL(blob);
      
      // Clean up previous subtitle URL
      if (subtitleUrl) {
        URL.revokeObjectURL(subtitleUrl);
      }
      
      setSubtitleUrl(url);
      console.log(`✅ Subtitles loaded successfully`);

    } catch (err) {
      console.error('❌ Error loading subtitles:', err);
      
      if (err instanceof SubtitleThrottlingError) {
        setSubtitleError('Translation service is busy. Trying to load original subtitles...');
        
        // Try to load non-translated subtitles as fallback
        try {
          const job = jobData.find(j => j.media_name === citation.media_name);
          if (job) {
            const vttContent = await retrieveSubtitles(job.UUID, username, idToken);
            const blob = new Blob([vttContent], { type: 'text/vtt' });
            const url = URL.createObjectURL(blob);
            
            if (subtitleUrl) {
              URL.revokeObjectURL(subtitleUrl);
            }
            
            setSubtitleUrl(url);
            setSubtitleError('Translation unavailable - showing original subtitles');
          }
        } catch (fallbackErr) {
          setSubtitleError('Failed to load subtitles. Please try again later.');
        }
      } else if (err instanceof SubtitleError) {
        setSubtitleError(err.message);
      } else {
        setSubtitleError('Failed to load subtitles. Please try again.');
      }
    } finally {
      setIsLoadingSubtitles(false);
      setIsTranslating(false);
    }
  };

  useEffect(() => {
    if (citation && isVisible) {
      loadMedia();
    }
  }, [citation, isVisible]);

  useEffect(() => {
    if (citation && isVisible && displaySubtitles && username && idToken) {
      loadSubtitles();
    } else {
      // Clear subtitles if not needed
      setSubtitleUrl('');
      setSubtitleError('');
    }
  }, [citation, isVisible, displaySubtitles, translationLanguage, username, idToken]);

  // Clean up blob URLs when component unmounts or citation changes
  useEffect(() => {
    return () => {
      if (subtitleUrl) {
        URL.revokeObjectURL(subtitleUrl);
      }
    };
  }, [subtitleUrl]);

  const handleMediaLoaded = () => {
    if (videoRef.current && citation) {
      // Set the current time to the citation timestamp
      videoRef.current.currentTime = citation.timestamp;
      console.log(`⏰ Set media time to ${citation.timestamp}s`);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const currentTime = Math.floor(videoRef.current.currentTime);
      // Optional: Add visual indicator when we're near the citation timestamp
      if (Math.abs(currentTime - (citation?.timestamp || 0)) < 2) {
        // Could add highlighting or other visual feedback here
      }
    }
  };

  if (!citation) return null;

  return (
    <Modal
      visible={isVisible}
      onDismiss={onClose}
      header={`${citation.media_name} - Citation ${citation.id}`}
      size="large"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onClose}>
              Close
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween size="m">
        <Box>
          <Box variant="small" color="text-body-secondary">
            Playing from timestamp: {Math.floor(citation.timestamp / 60)}:{(citation.timestamp % 60).toFixed(0).padStart(2, '0')}
          </Box>
        </Box>

        {isLoading && (
          <Box textAlign="center" padding="l">
            <Spinner size="large" />
            <Box variant="p" margin={{ top: "s" }}>
              Loading media...
            </Box>
          </Box>
        )}

        {error && (
          <Alert type="error" dismissible onDismiss={() => setError('')}>
            {error}
          </Alert>
        )}

        {mediaUrl && !isLoading && (
          <Box>
            {isLoadingSubtitles && (
              <Box margin={{ bottom: "s" }}>
                <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                  <Spinner size="normal" />
                  <Box variant="small" color="text-body-secondary">
                    {isTranslating ? `Translating subtitles to ${translationLanguage}...` : 'Loading subtitles...'}
                  </Box>
                </SpaceBetween>
              </Box>
            )}

            {subtitleError && (
              <Alert 
                type={subtitleError.includes('original subtitles') ? 'warning' : 'error'}
                dismissible 
                onDismiss={() => setSubtitleError('')}
              >
                {subtitleError}
              </Alert>
            )}

            {mediaType === 'video' ? (
              <video
                ref={videoRef}
                controls
                width="100%"
                style={{ maxHeight: '400px' }}
                onLoadedData={handleMediaLoaded}
                onTimeUpdate={handleTimeUpdate}
                preload="metadata"
              >
                <source src={mediaUrl} />
                {subtitleUrl && (
                  <track
                    kind="subtitles"
                    src={subtitleUrl}
                    srcLang="en"
                    label={translationLanguage ? `Subtitles (${translationLanguage})` : 'Subtitles'}
                    default
                  />
                )}
                Your browser does not support the video element.
              </video>
            ) : (
              <audio
                ref={videoRef as any}
                controls
                style={{ width: '100%' }}
                onLoadedData={handleMediaLoaded}
                onTimeUpdate={handleTimeUpdate}
                preload="metadata"
              >
                <source src={mediaUrl} />
                {subtitleUrl && (
                  <track
                    kind="subtitles"
                    src={subtitleUrl}
                    srcLang="en"
                    label={translationLanguage ? `Subtitles (${translationLanguage})` : 'Subtitles'}
                    default
                  />
                )}
                Your browser does not support the audio element.
              </audio>
            )}
          </Box>
        )}

        <Box variant="small" color="text-body-secondary">
          <strong>Citation:</strong> {citation.media_name} at {citation.timestamp}s
        </Box>
      </SpaceBetween>
    </Modal>
  );
};

export default MediaPlayer;
