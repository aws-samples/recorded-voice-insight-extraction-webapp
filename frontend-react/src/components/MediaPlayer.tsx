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

interface MediaPlayerProps {
  citation: ProcessedCitation | null;
  isVisible: boolean;
  onClose: () => void;
  onGetPresignedUrl: (mediaName: string) => Promise<string>;
}

const MediaPlayer: React.FC<MediaPlayerProps> = ({
  citation,
  isVisible,
  onClose,
  onGetPresignedUrl
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [mediaUrl, setMediaUrl] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [mediaType, setMediaType] = useState<'video' | 'audio'>('video');

  useEffect(() => {
    if (citation && isVisible) {
      loadMedia();
    }
  }, [citation, isVisible]);

  const loadMedia = async () => {
    if (!citation) return;

    setIsLoading(true);
    setError('');
    
    try {
      console.log(`🎬 Loading media: ${citation.media_name} at ${citation.timestamp}s`);
      
      // Get presigned URL for the media file
      const url = await onGetPresignedUrl(citation.media_name);
      setMediaUrl(url);
      
      // Determine media type based on file extension
      const extension = citation.media_name.toLowerCase().split('.').pop();
      const videoExtensions = ['mp4', 'webm', 'ogg', 'mov', 'avi'];
      const audioExtensions = ['mp3', 'wav', 'ogg', 'm4a', 'aac'];
      
      if (videoExtensions.includes(extension || '')) {
        setMediaType('video');
      } else if (audioExtensions.includes(extension || '')) {
        setMediaType('audio');
      } else {
        setMediaType('video'); // Default to video
      }
      
    } catch (err) {
      console.error('Error loading media:', err);
      setError(err instanceof Error ? err.message : 'Failed to load media');
    } finally {
      setIsLoading(false);
    }
  };

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
