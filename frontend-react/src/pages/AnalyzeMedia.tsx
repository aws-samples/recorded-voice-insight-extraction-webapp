// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React, { useEffect, useState } from 'react';
import {
  Container,
  Header,
  Select,
  SpaceBetween,
  Button,
  Alert,
} from '@cloudscape-design/components';
import { AnalysisResults } from '../components/AnalysisResults';
import { useAnalysisApi } from '../hooks/useAnalysisApi';
import { 
  AnalysisPageState,
  Job
} from '../types/analysis';

const initialState: AnalysisPageState = {
  selectedMediaName: null,
  selectedAnalysisTemplate: null,
  analysisResult: null,
  isLoading: false,
  error: null,
  completedJobs: [],
  analysisTemplates: [],
};

export const AnalyzeMedia: React.FC = () => {
  const [state, setState] = useState<AnalysisPageState>(initialState);
  const username = localStorage.getItem('username') || ''; // Get from your auth context
  const { retrieveAllItems, getAnalysisTemplates, submitAnalysis } = useAnalysisApi();

  // Load completed jobs and analysis templates on component mount
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [jobs, templates] = await Promise.all([
          retrieveAllItems(username),
          getAnalysisTemplates()
        ]);

        setState(prev => ({
          ...prev,
          completedJobs: jobs.filter((job: Job) => job.job_status === 'Completed'),
          analysisTemplates: templates
        }));
      } catch (error) {
        setState(prev => ({
          ...prev,
          error: 'Failed to load initial data. Please try again.'
        }));
      }
    };

    loadInitialData();
  }, [username]);

  // Handle media selection
  const handleMediaChange = (event: any) => {
    setState(prev => ({
      ...prev,
      selectedMediaName: event.detail.selectedOption.value as string,
      analysisResult: null,
      error: null
    }));
  };

  // Handle analysis template selection
  const handleTemplateChange = (event: any) => {
    setState(prev => ({
      ...prev,
      selectedAnalysisTemplate: event.detail.selectedOption.value as string,
      analysisResult: null,
      error: null
    }));
  };

  // Run analysis
  const handleRunAnalysis = async () => {
    if (!state.selectedMediaName || !state.selectedAnalysisTemplate) {
      setState(prev => ({
        ...prev,
        error: 'Please select both a media file and an analysis type.'
      }));
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const templateId = state.analysisTemplates.find(
        t => t.template_short_name === state.selectedAnalysisTemplate
      )?.template_id;

      if (!templateId) {
        throw new Error('Invalid template selected');
      }

      const template = state.analysisTemplates.find(t => t.template_id === templateId);
      if (!template) {
        throw new Error('Template not found');
      }

      const result = await submitAnalysis(
        username,
        [state.selectedMediaName],
        template
      );

      setState(prev => ({
        ...prev,
        analysisResult: result, // result is now the analysis text directly
        isLoading: false
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: 'Failed to perform analysis. Please try again.',
        isLoading: false
      }));
    }
  };

  // Prepare options for select components
  const mediaOptions = state.completedJobs.map(job => ({
    label: job.media_name,
    value: job.media_name
  }));

  const templateOptions = state.analysisTemplates.map(template => ({
    label: template.template_short_name,
    value: template.template_short_name,
    description: template.template_description
  }));

  return (
    <SpaceBetween size="l">
      <Container header={<Header variant="h1">Analyze Your Media</Header>}>
        <SpaceBetween size="m">
          {state.error && (
            <Alert type="error" header="Error">
              {state.error}
            </Alert>
          )}

          <Select
            selectedOption={
              state.selectedMediaName
                ? { label: state.selectedMediaName, value: state.selectedMediaName }
                : null
            }
            onChange={handleMediaChange}
            options={mediaOptions}
            placeholder="Select a media file to analyze"
            filteringType="auto"
            selectedAriaLabel="Selected"
          />

          <Select
            selectedOption={
              state.selectedAnalysisTemplate
                ? {
                    label: state.selectedAnalysisTemplate,
                    value: state.selectedAnalysisTemplate
                  }
                : null
            }
            onChange={handleTemplateChange}
            options={templateOptions}
            placeholder="Select an analysis type"
            filteringType="auto"
            selectedAriaLabel="Selected"
          />

          <Button
            variant="primary"
            onClick={handleRunAnalysis}
            loading={state.isLoading}
            disabled={!state.selectedMediaName || !state.selectedAnalysisTemplate}
          >
            Run Analysis
          </Button>
        </SpaceBetween>
      </Container>

      <AnalysisResults
        result={state.analysisResult || ''}
        isLoading={state.isLoading}
        error={state.error || undefined}
      />
    </SpaceBetween>
  );
};

export default AnalyzeMedia;
