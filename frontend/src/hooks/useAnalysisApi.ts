// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { useState, useCallback } from 'react';
import { analysisApi } from '../api/analysis';
import { Job, AnalysisTemplate } from '../types/analysis';

/**
 * Hook for analysis API operations with loading states
 */
export const useAnalysisApi = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const retrieveAllItems = useCallback(async (username: string, maxRows?: number): Promise<Job[]> => {
    setLoading(true);
    setError(null);
    try {
      const result = await analysisApi.retrieveAllItems(username, maxRows);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to retrieve items';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getAnalysisTemplates = useCallback(async (): Promise<AnalysisTemplate[]> => {
    setLoading(true);
    setError(null);
    try {
      const result = await analysisApi.getAnalysisTemplates();
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get analysis templates';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const submitAnalysis = useCallback(async (
    username: string,
    selectedFiles: string[],
    template: AnalysisTemplate,
    customPrompt?: string
  ): Promise<string> => {
    setLoading(true);
    setError(null);
    try {
      const result = await analysisApi.submitAnalysis(username, selectedFiles, template, customPrompt);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to submit analysis';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getJobStatus = useCallback(async (jobId: string): Promise<Job> => {
    setLoading(true);
    setError(null);
    try {
      const result = await analysisApi.getJobStatus(jobId);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get job status';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteJob = useCallback(async (jobId: string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      await analysisApi.deleteJob(jobId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete job';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getPresignedUrl = useCallback(async (key: string): Promise<{ url: string }> => {
    setLoading(true);
    setError(null);
    try {
      const result = await analysisApi.getPresignedUrl(key);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get presigned URL';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    loading,
    error,
    clearError,
    retrieveAllItems,
    getAnalysisTemplates,
    submitAnalysis,
    getJobStatus,
    deleteJob,
    getPresignedUrl,
  };
};
