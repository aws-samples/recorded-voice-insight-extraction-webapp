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
import { urlDecodeFilename } from '../utils/fileUtils';
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
  const [lastTranslatedTimestamp, setLastTranslatedTimestamp] = useState<number>(-1);
  const [isUserSeeking, setIsUserSeeking] = useState<boolean>(false);
  const [wasPlayingBeforeTranslation, setWasPlayingBeforeTranslation] = useState<boolean>(false);

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

  const loadSubtitles = async (startTime?: number, pauseVideo: boolean = false) => {
    if (!citation || !username || !idToken) return;

    // Use provided startTime or citation timestamp
    const translationStartTime = startTime !== undefined ? startTime : citation.timestamp;

    // Capture the playing state early to avoid race conditions
    let wasVideoPlayingBeforeTranslation = false;

    // If we need to pause the video during translation
    if (pauseVideo && videoRef.current && translationLanguage) {
      wasVideoPlayingBeforeTranslation = !videoRef.current.paused;
      setWasPlayingBeforeTranslation(wasVideoPlayingBeforeTranslation);
      
      console.log(`🎬 Video state before translation: ${wasVideoPlayingBeforeTranslation ? 'PLAYING' : 'PAUSED'}`);
      
      if (wasVideoPlayingBeforeTranslation) {
        videoRef.current.pause();
        console.log(`⏸️ Paused video for subtitle translation`);
      } else {
        console.log(`⏸️ Video was already paused, no need to pause again`);
      }
      
      // Temporarily hide existing subtitles by removing the track
      const tracks = videoRef.current.textTracks;
      for (let i = 0; i < tracks.length; i++) {
        tracks[i].mode = 'hidden';
      }
      console.log(`👁️ Hidden ${tracks.length} subtitle tracks during translation`);
    }

    setIsLoadingSubtitles(true);
    setSubtitleError('');
    setIsTranslating(!!translationLanguage);
    
    try {
      // Find the job ID for this media file
      const job = jobData.find(j => j.media_name === citation.media_name);
      if (!job) {
        throw new Error(`Could not find job data for media: ${citation.media_name}`);
      }

      console.log(`🎬 Loading subtitles for: ${citation.media_name} (Job ID: ${job.UUID}) at ${translationStartTime}s`);
      
      let translationDuration: number | undefined;
      let translationDestinationLanguage: string | undefined;

      // If translation is requested, set parameters
      if (translationLanguage) {
        // Start translation 5 seconds before current position (minimum 0)
        const adjustedStartTime = Math.max(0, translationStartTime - 5);
        translationDuration = 30; // seconds - translate 30 seconds from the adjusted start time
        translationDestinationLanguage = translationLanguage;
        console.log(`🌐 Translating subtitles to ${translationLanguage} from ${adjustedStartTime}s (${translationStartTime - adjustedStartTime}s before current) for ${translationDuration}s`);
        
        // Use the adjusted start time for the API call
        const vttContent = await retrieveSubtitles(
          job.UUID,
          username,
          adjustedStartTime,
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
        setLastTranslatedTimestamp(translationStartTime); // Still track the original timestamp for threshold calculations
        console.log(`✅ Subtitles loaded successfully for timestamp ${translationStartTime}s (translated from ${adjustedStartTime}s)`);
      } else {
        // No translation needed, load original subtitles
        const vttContent = await retrieveSubtitles(
          job.UUID,
          username
        );

        // Create a blob URL for the VTT content
        const blob = new Blob([vttContent], { type: 'text/vtt' });
        const url = URL.createObjectURL(blob);
        
        // Clean up previous subtitle URL
        if (subtitleUrl) {
          URL.revokeObjectURL(subtitleUrl);
        }
        
        setSubtitleUrl(url);
        setLastTranslatedTimestamp(translationStartTime);
        console.log(`✅ Original subtitles loaded successfully for timestamp ${translationStartTime}s`);
      }

      // Re-enable subtitle tracks after new subtitles are loaded
      if (pauseVideo && videoRef.current) {
        // Small delay to ensure the new track is loaded
        setTimeout(() => {
          if (videoRef.current) {
            const tracks = videoRef.current.textTracks;
            for (let i = 0; i < tracks.length; i++) {
              if (tracks[i].kind === 'subtitles') {
                tracks[i].mode = 'showing';
                console.log(`👁️ Re-enabled subtitle track ${i}`);
              }
            }
          }
        }, 200);
      }

      // Resume video playback if it was playing before translation
      // Use the captured state to avoid race conditions
      if (pauseVideo && videoRef.current && wasVideoPlayingBeforeTranslation) {
        console.log(`🎬 Preparing to resume video playback (was playing: ${wasVideoPlayingBeforeTranslation})`);
        // Small delay to ensure subtitle track is loaded
        setTimeout(() => {
          if (videoRef.current && wasVideoPlayingBeforeTranslation) {
            console.log(`▶️ Attempting to resume video playback...`);
            videoRef.current.play().then(() => {
              console.log(`✅ Successfully resumed video playback after subtitle translation`);
            }).catch((error) => {
              console.error(`❌ Failed to resume video playback:`, error);
              // Try again after a short delay
              setTimeout(() => {
                if (videoRef.current) {
                  videoRef.current.play().catch(e => console.error('❌ Second resume attempt failed:', e));
                }
              }, 500);
            });
          } else {
            console.log(`⚠️ Cannot resume - video ref or playing state lost`);
          }
        }, 300); // Slightly longer delay to ensure subtitles are ready
      } else if (pauseVideo) {
        console.log(`⏸️ Video was paused before translation, not resuming playback`);
      }

    } catch (err) {
      console.error('❌ Error loading subtitles:', err);
      
      // Capture the state for resuming playback even on error
      const shouldResumePlaybackOnError = pauseVideo && videoRef.current && wasVideoPlayingBeforeTranslation;
      
      if (err instanceof SubtitleThrottlingError) {
        setSubtitleError('Translation service is busy. Trying to load original subtitles...');
        
        // Try to load non-translated subtitles as fallback
        try {
          const job = jobData.find(j => j.media_name === citation.media_name);
          if (job) {
            const vttContent = await retrieveSubtitles(job.UUID, username);
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
      
      // Resume video playback even if subtitle loading failed
      if (shouldResumePlaybackOnError) {
        console.log(`🎬 Resuming video playback despite subtitle error (was playing: ${wasVideoPlayingBeforeTranslation})`);
        setTimeout(() => {
          if (videoRef.current && wasVideoPlayingBeforeTranslation) {
            console.log(`▶️ Attempting to resume video after error...`);
            videoRef.current.play().then(() => {
              console.log(`✅ Successfully resumed video playback after subtitle error`);
            }).catch((playError) => {
              console.error(`❌ Failed to resume video playback after error:`, playError);
            });
          }
        }, 100); // Shorter delay since we're not waiting for subtitles
      }
    } finally {
      setIsLoadingSubtitles(false);
      setIsTranslating(false);
      // Don't reset wasPlayingBeforeTranslation here to avoid race conditions
      // It will be reset when the component unmounts or citation changes
    }
  };

  useEffect(() => {
    if (citation && isVisible) {
      loadMedia();
    }
  }, [citation, isVisible]);

  useEffect(() => {
    if (citation && isVisible && displaySubtitles && username && idToken) {
      // Reset the last translated timestamp when citation changes
      setLastTranslatedTimestamp(-1);
      loadSubtitles();
    } else {
      // Clear subtitles if not needed
      setSubtitleUrl('');
      setSubtitleError('');
      setLastTranslatedTimestamp(-1);
      setWasPlayingBeforeTranslation(false); // Reset playing state when subtitles disabled
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

  // Enable subtitle tracks when subtitleUrl changes
  useEffect(() => {
    if (subtitleUrl && videoRef.current && displaySubtitles) {
      // Small delay to ensure the track element is loaded
      setTimeout(() => {
        if (videoRef.current) {
          const tracks = videoRef.current.textTracks;
          for (let i = 0; i < tracks.length; i++) {
            if (tracks[i].kind === 'subtitles') {
              tracks[i].mode = 'showing';
              console.log(`👁️ Enabled subtitle track ${i} after URL change`);
            }
          }
        }
      }, 100);
    }
  }, [subtitleUrl, displaySubtitles]);

  const handleMediaLoaded = () => {
    if (videoRef.current && citation) {
      // Set the current time to the citation timestamp
      videoRef.current.currentTime = citation.timestamp;
      console.log(`⏰ Set media time to ${citation.timestamp}s`);
      
      // Ensure subtitle tracks are enabled if subtitles are displayed
      if (displaySubtitles && subtitleUrl) {
        setTimeout(() => {
          if (videoRef.current) {
            const tracks = videoRef.current.textTracks;
            for (let i = 0; i < tracks.length; i++) {
              if (tracks[i].kind === 'subtitles') {
                tracks[i].mode = 'showing';
                console.log(`👁️ Enabled subtitle track ${i} on media load`);
              }
            }
          }
        }, 100);
      }
    }
  };

  const handleSeeking = () => {
    setIsUserSeeking(true);
    console.log(`🔍 User is seeking...`);
  };

  const handleSeeked = () => {
    if (videoRef.current && translationLanguage && displaySubtitles) {
      const currentTime = Math.floor(videoRef.current.currentTime);
      console.log(`🎯 User seeked to ${currentTime}s (last translated: ${lastTranslatedTimestamp}s)`);
      
      // Calculate distance from last translated position
      const distanceFromLastTranslation = Math.abs(currentTime - lastTranslatedTimestamp);
      
      // Reload subtitles if:
      // 1. We've moved significantly (more than 15 seconds) OR
      // 2. This is the first translation (lastTranslatedTimestamp is -1) OR  
      // 3. We're outside the 30-second translation window from last position
      const shouldReloadSubtitles = (
        (lastTranslatedTimestamp === -1) || // First translation
        (distanceFromLastTranslation > 15) || // Moved significantly
        (currentTime < lastTranslatedTimestamp || currentTime > lastTranslatedTimestamp + 30) // Outside translation window
      ) && !isLoadingSubtitles;
      
      if (shouldReloadSubtitles) {
        console.log(`🔄 Reloading subtitles for new position: ${currentTime}s (distance: ${distanceFromLastTranslation}s)`);
        loadSubtitles(currentTime, true); // Pass true to pause video during translation
      } else {
        console.log(`⏭️ Skipping subtitle reload - within acceptable range (distance: ${distanceFromLastTranslation}s)`);
      }
    }
    setIsUserSeeking(false);
  };

  const handlePlay = () => {
    if (videoRef.current && translationLanguage && displaySubtitles && !isUserSeeking) {
      const currentTime = Math.floor(videoRef.current.currentTime);
      console.log(`▶️ User pressed play at ${currentTime}s (last translated: ${lastTranslatedTimestamp}s)`);
      
      // Calculate distance from last translated position
      const distanceFromLastTranslation = Math.abs(currentTime - lastTranslatedTimestamp);
      
      // Same logic as handleSeeked
      const shouldReloadSubtitles = (
        (lastTranslatedTimestamp === -1) || // First translation
        (distanceFromLastTranslation > 15) || // Moved significantly
        (currentTime < lastTranslatedTimestamp || currentTime > lastTranslatedTimestamp + 30) // Outside translation window
      ) && !isLoadingSubtitles;
      
      if (shouldReloadSubtitles) {
        console.log(`🔄 Reloading subtitles after play: ${currentTime}s (distance: ${distanceFromLastTranslation}s)`);
        loadSubtitles(currentTime, true); // Pass true to pause video during translation
      } else {
        console.log(`⏭️ Skipping subtitle reload after play - within acceptable range (distance: ${distanceFromLastTranslation}s)`);
      }
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
      header={`${urlDecodeFilename(citation.media_name)} - Citation ${citation.id}`}
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
            {subtitleError && (
              <Alert 
                type={subtitleError.includes('original subtitles') ? 'warning' : 'error'}
                dismissible 
                onDismiss={() => setSubtitleError('')}
              >
                {subtitleError}
              </Alert>
            )}

            <div style={{ position: 'relative' }}>
              {mediaType === 'video' ? (
                <video
                  ref={videoRef}
                  controls
                  width="100%"
                  style={{ maxHeight: '400px' }}
                  onLoadedData={handleMediaLoaded}
                  onTimeUpdate={handleTimeUpdate}
                  onSeeking={handleSeeking}
                  onSeeked={handleSeeked}
                  onPlay={handlePlay}
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
                  onSeeking={handleSeeking}
                  onSeeked={handleSeeked}
                  onPlay={handlePlay}
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
            </div>

            {isLoadingSubtitles && (
              <Box margin={{ top: "s" }} textAlign="center">
                <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                  <Spinner size="normal" />
                  <Box variant="h4" color="text-status-info">
                    {isTranslating 
                      ? `🌐 Translating subtitles to ${translationLanguage}...` 
                      : 'Loading subtitles...'
                    }
                    {isTranslating && wasPlayingBeforeTranslation && (
                      <span> - Video paused</span>
                    )}
                  </Box>
                </SpaceBetween>
              </Box>
            )}
          </Box>
        )}

        <Box variant="small" color="text-body-secondary">
          <strong>Citation:</strong> {urlDecodeFilename(citation.media_name)} at {citation.timestamp}s
        </Box>
      </SpaceBetween>
    </Modal>
  );
};

export default MediaPlayer;
