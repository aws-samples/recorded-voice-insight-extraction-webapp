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
  Grid,
  ContentLayout,
  Box,
  Textarea,
  Input,
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

// Create Analysis Form State
interface CreateAnalysisState {
  analysisName: string;
  analysisDescription: string;
  analysisPrompt: string;
  isCreating: boolean;
  createError: string | null;
  createSuccess: string | null;
}

export const AnalyzeMedia: React.FC = () => {
  const [state, setState] = useState<AnalysisPageState>(initialState);
  const [createState, setCreateState] = useState<CreateAnalysisState>({
    analysisName: '',
    analysisDescription: '',
    analysisPrompt: '',
    isCreating: false,
    createError: null,
    createSuccess: null,
  });
  
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
          completedJobs: jobs.filter((job: Job) => 
            job.job_status === 'Completed' || job.job_status === 'BDA Analysis Complete'
          ),
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

  // Create Analysis Handlers
  const handleCreateAnalysis = async () => {
    if (!createState.analysisName.trim() || !createState.analysisDescription.trim() || !createState.analysisPrompt.trim()) {
      setCreateState(prev => ({
        ...prev,
        createError: 'Please fill in all required fields (Analysis Name, Description, and Analysis Prompt).'
      }));
      return;
    }

    setCreateState(prev => ({ ...prev, isCreating: true, createError: null, createSuccess: null }));

    try {
      const authToken = localStorage.getItem('authToken');
      if (!authToken) {
        throw new Error('Authentication token not found');
      }

      const response = await fetch('/api/analysis-templates', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': authToken,
        },
        body: JSON.stringify({
          template_short_name: createState.analysisName,
          template_description: createState.analysisDescription,
          template_prompt: createState.analysisPrompt,
          bedrock_kwargs: { temperature: 0.1, max_tokens: 2000 }
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const newTemplate = await response.json();
      
      // Refresh the templates list
      const updatedTemplates = await getAnalysisTemplates();
      setState(prev => ({ ...prev, analysisTemplates: updatedTemplates }));

      // Reset form and show success
      setCreateState({
        analysisName: '',
        analysisDescription: '',
        analysisPrompt: '',
        isCreating: false,
        createError: null,
        createSuccess: `Analysis template "${newTemplate.template_short_name}" created successfully!`
      });

    } catch (error) {
      console.error('Error creating analysis template:', error);
      setCreateState(prev => ({
        ...prev,
        isCreating: false,
        createError: error instanceof Error ? error.message : 'Failed to create analysis template. Please try again.'
      }));
    }
  };

  return (
    <ContentLayout
      header={
        <Header
          variant="h1"
          description="Run analysis on your media files or create custom analysis templates"
        >
          Analyze Your Media
        </Header>
      }
    >
      <SpaceBetween size="l">
        <Grid
          gridDefinition={[
            { colspan: { default: 12, xs: 6 } }, // Run an Analysis - Upper Left
            { colspan: { default: 12, xs: 6 } }, // Create an Analysis - Upper Right
            { colspan: 12 } // Analysis Results - Full Width Below
          ]}
        >
          {/* Run an Analysis Block - Upper Left */}
          <Container header={<Header variant="h2">Run an Analysis</Header>}>
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
                placeholder="Select an analysis template"
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

          {/* Create an Analysis Block - Upper Right */}
          <Container header={<Header variant="h2">Create an Analysis</Header>}>
            <SpaceBetween size="m">
              {createState.createError && (
                <Alert type="error" dismissible onDismiss={() => setCreateState(prev => ({ ...prev, createError: null }))}>
                  {createState.createError}
                </Alert>
              )}

              {createState.createSuccess && (
                <Alert type="success" dismissible onDismiss={() => setCreateState(prev => ({ ...prev, createSuccess: null }))}>
                  {createState.createSuccess}
                </Alert>
              )}

              <Input
                value={createState.analysisName}
                onChange={({ detail }) => setCreateState(prev => ({ ...prev, analysisName: detail.value }))}
                placeholder="Bullet Point Summary"
                disabled={createState.isCreating}
              />

              <Input
                value={createState.analysisDescription}
                onChange={({ detail }) => setCreateState(prev => ({ ...prev, analysisDescription: detail.value }))}
                placeholder="Generates a short summary in bullet points"
                disabled={createState.isCreating}
              />

              <Textarea
                value={createState.analysisPrompt}
                onChange={({ detail }) => setCreateState(prev => ({ ...prev, analysisPrompt: detail.value }))}
                placeholder={'Enter your analysis prompt here. Be sure to include the keyword "{transcript}" where the media transcript will be added. For example:\n\nAnalyze the following transcript of a meeting:\n{transcript}\nNow write a bullet point summary of the transcript.'}
                rows={6}
                disabled={createState.isCreating}
              />

              <Button
                variant="primary"
                onClick={handleCreateAnalysis}
                loading={createState.isCreating}
                disabled={!createState.analysisName.trim() || !createState.analysisDescription.trim() || !createState.analysisPrompt.trim()}
              >
                Store Analysis
              </Button>
            </SpaceBetween>
          </Container>

          {/* Analysis Results Block - Full Width Below */}
          <Container
            header={
              <Header variant="h2">
                Analysis Results
              </Header>
            }
          >
            {state.error && (
              <Alert type="error" header="Analysis Error">
                {state.error}
              </Alert>
            )}

            {state.isLoading && (
              <Box textAlign="center" padding="l">
                <Box variant="p" padding={{ top: "s" }}>
                  Running analysis... This may take a few moments.
                </Box>
              </Box>
            )}

            {!state.isLoading && !state.error && !state.analysisResult && (
              <Box variant="p" color="text-status-inactive">
                Analysis results will be displayed here when complete.
              </Box>
            )}

            {state.analysisResult && (
              <Textarea
                value={state.analysisResult}
                readOnly
                rows={15}
                placeholder="Analysis results will appear here..."
                spellcheck={false}
              />
            )}
          </Container>
        </Grid>
      </SpaceBetween>
    </ContentLayout>
  );
};

export default AnalyzeMedia;
