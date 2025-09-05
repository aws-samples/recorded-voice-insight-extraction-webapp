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
import { useAnalysisApi } from '../hooks/useAnalysisApi';
import { urlDecodeFilename } from '../utils/fileUtils';
import useHttp from '../hooks/useHttp';
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
  currentView: 'menu' | 'create' | 'edit' | 'remove';
  selectedTemplateForEdit: string | null; // template_id of selected template for editing
  editingTemplateId: string | null; // ID of template being edited
  selectedTemplateForDelete: string | null; // template_id of selected template for deletion
  isDeleting: boolean;
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
    currentView: 'menu',
    selectedTemplateForEdit: null,
    editingTemplateId: null,
    selectedTemplateForDelete: null,
    isDeleting: false,
  });
  
  const username = localStorage.getItem('username') || ''; // Get from your auth context
  const { retrieveAllItems, getAnalysisTemplates, submitAnalysis } = useAnalysisApi();
  const http = useHttp();

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
    label: urlDecodeFilename(job.media_name),
    value: job.media_name
  }));

  const templateOptions = state.analysisTemplates.map(template => ({
    label: template.template_short_name,
    value: template.template_short_name,
    description: template.template_description
  }));

  // Get user-created templates only (exclude default templates)
  const userTemplates = state.analysisTemplates.filter(template => 
    template.user_id && template.user_id !== 'default'
  );

  const userTemplateOptions = userTemplates.map(template => ({
    label: template.template_short_name,
    value: template.template_id,
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
      const isEditing = createState.editingTemplateId !== null;
      const templateData = {
        template_short_name: createState.analysisName,
        template_description: createState.analysisDescription,
        template_prompt: createState.analysisPrompt,
        bedrock_kwargs: { temperature: 0.1, maxTokens: 2000 }
      };

      let response;
      if (isEditing) {
        // Update existing template
        response = await http.put(`/analysis-templates/${createState.editingTemplateId}`, templateData);
      } else {
        // Create new template
        response = await http.post('/analysis-templates', templateData);
      }

      const template = response.data;
      
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
        createSuccess: `Analysis template "${template.template_short_name}" ${isEditing ? 'updated' : 'created'} successfully!`,
        currentView: 'menu',
        selectedTemplateForEdit: null,
        editingTemplateId: null,
        selectedTemplateForDelete: null,
        isDeleting: false,
      });

    } catch (error: any) {
      console.error('Error saving analysis template:', error);
      let errorMessage = 'Failed to save analysis template. Please try again.';
      
      // Extract error message from response if available
      if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.response?.status) {
        errorMessage = `HTTP error! status: ${error.response.status}`;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setCreateState(prev => ({
        ...prev,
        isCreating: false,
        createError: errorMessage
      }));
    }
  };

  // Navigation handlers for Custom Analysis section
  const handleShowCreateForm = () => {
    setCreateState(prev => ({ 
      ...prev, 
      currentView: 'create',
      createError: null,
      createSuccess: null,
      analysisName: '',
      analysisDescription: '',
      analysisPrompt: '',
      editingTemplateId: null,
    }));
  };

  const handleShowEditForm = () => {
    setCreateState(prev => ({ 
      ...prev, 
      currentView: 'edit',
      createError: null,
      createSuccess: null,
      selectedTemplateForEdit: null,
      analysisName: '',
      analysisDescription: '',
      analysisPrompt: '',
      editingTemplateId: null,
    }));
  };

  const handleShowRemoveForm = () => {
    setCreateState(prev => ({ 
      ...prev, 
      currentView: 'remove',
      createError: null,
      createSuccess: null,
      selectedTemplateForDelete: null,
    }));
  };

  const handleBackToMenu = () => {
    setCreateState(prev => ({ 
      ...prev, 
      currentView: 'menu',
      analysisName: '',
      analysisDescription: '',
      analysisPrompt: '',
      createError: null,
      createSuccess: null,
      selectedTemplateForEdit: null,
      editingTemplateId: null,
      selectedTemplateForDelete: null,
      isDeleting: false,
    }));
  };

  // Handle template selection for editing
  const handleTemplateSelectionForEdit = ({ detail }: any) => {
    const templateId = detail.selectedOption.value;
    const selectedTemplate = userTemplates.find(template => template.template_id === templateId);
    
    if (selectedTemplate) {
      setCreateState(prev => ({
        ...prev,
        selectedTemplateForEdit: templateId,
        analysisName: selectedTemplate.template_short_name,
        analysisDescription: selectedTemplate.template_description,
        analysisPrompt: selectedTemplate.template_prompt,
        editingTemplateId: templateId,
      }));
    }
  };

  // Handle template selection for deletion
  const handleTemplateSelectionForDelete = ({ detail }: any) => {
    const templateId = detail.selectedOption.value;
    setCreateState(prev => ({
      ...prev,
      selectedTemplateForDelete: templateId,
    }));
  };

  // Handle template deletion
  const handleDeleteAnalysis = async () => {
    if (!createState.selectedTemplateForDelete) {
      return;
    }

    setCreateState(prev => ({ ...prev, isDeleting: true, createError: null }));

    try {
      await http.delete(`/analysis-templates/${createState.selectedTemplateForDelete}`);
      
      // Refresh the templates list
      const updatedTemplates = await getAnalysisTemplates();
      setState(prev => ({ ...prev, analysisTemplates: updatedTemplates }));

      // Get the deleted template name for success message
      const deletedTemplate = userTemplates.find(t => t.template_id === createState.selectedTemplateForDelete);
      const templateName = deletedTemplate?.template_short_name || 'Template';

      // Reset form and show success
      setCreateState({
        analysisName: '',
        analysisDescription: '',
        analysisPrompt: '',
        isCreating: false,
        createError: null,
        createSuccess: `Analysis template "${templateName}" deleted successfully!`,
        currentView: 'menu',
        selectedTemplateForEdit: null,
        editingTemplateId: null,
        selectedTemplateForDelete: null,
        isDeleting: false,
      });

    } catch (error: any) {
      console.error('Error deleting analysis template:', error);
      let errorMessage = 'Failed to delete analysis template. Please try again.';
      
      // Extract error message from response if available
      if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.response?.status) {
        errorMessage = `HTTP error! status: ${error.response.status}`;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setCreateState(prev => ({
        ...prev,
        isDeleting: false,
        createError: errorMessage
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

          {/* Custom Analysis Block - Upper Right */}
          <Container header={<Header variant="h2">Custom Analysis</Header>}>
            <SpaceBetween size="m">
              {createState.createSuccess && (
                <Alert type="success" dismissible onDismiss={() => setCreateState(prev => ({ ...prev, createSuccess: null }))}>
                  {createState.createSuccess}
                </Alert>
              )}

              {createState.currentView === 'menu' && (
                <SpaceBetween size="s">
                  <Button
                    variant="primary"
                    onClick={handleShowCreateForm}
                    fullWidth
                  >
                    Create a new analysis
                  </Button>
                  <Button
                    variant="normal"
                    onClick={handleShowEditForm}
                    fullWidth
                  >
                    Edit an existing analysis
                  </Button>
                  <Button
                    variant="normal"
                    onClick={handleShowRemoveForm}
                    fullWidth
                  >
                    Remove an analysis
                  </Button>
                </SpaceBetween>
              )}

              {createState.currentView === 'create' && (
                <SpaceBetween size="m">
                  {createState.createError && (
                    <Alert type="error" dismissible onDismiss={() => setCreateState(prev => ({ ...prev, createError: null }))}>
                      {createState.createError}
                    </Alert>
                  )}

                  <div>
                    <Box variant="awsui-key-label">Name</Box>
                    <Input
                      value={createState.analysisName}
                      onChange={({ detail }) => setCreateState(prev => ({ ...prev, analysisName: detail.value }))}
                      placeholder="Bullet Point Summary"
                      disabled={createState.isCreating}
                    />
                  </div>

                  <div>
                    <Box variant="awsui-key-label">Description</Box>
                    <Input
                      value={createState.analysisDescription}
                      onChange={({ detail }) => setCreateState(prev => ({ ...prev, analysisDescription: detail.value }))}
                      placeholder="Generates a short summary in bullet points"
                      disabled={createState.isCreating}
                    />
                  </div>

                  <div>
                    <Box variant="awsui-key-label">Prompt</Box>
                    <Textarea
                      value={createState.analysisPrompt}
                      onChange={({ detail }) => setCreateState(prev => ({ ...prev, analysisPrompt: detail.value }))}
                      placeholder={'Enter your analysis prompt here. Be sure to include the keyword "{transcript}" where the media transcript will be added. For example:\n\nAnalyze the following transcript of a meeting:\n{transcript}\nNow write a bullet point summary of the transcript.'}
                      rows={6}
                      disabled={createState.isCreating}
                    />
                  </div>

                  <SpaceBetween size="s" direction="horizontal">
                    <Button
                      variant="primary"
                      onClick={handleCreateAnalysis}
                      loading={createState.isCreating}
                      disabled={!createState.analysisName.trim() || !createState.analysisDescription.trim() || !createState.analysisPrompt.trim()}
                    >
                      Store Analysis
                    </Button>
                    <Button
                      variant="normal"
                      onClick={handleBackToMenu}
                      disabled={createState.isCreating}
                    >
                      Back
                    </Button>
                  </SpaceBetween>
                </SpaceBetween>
              )}

              {createState.currentView === 'edit' && (
                <SpaceBetween size="m">
                  {createState.createError && (
                    <Alert type="error" dismissible onDismiss={() => setCreateState(prev => ({ ...prev, createError: null }))}>
                      {createState.createError}
                    </Alert>
                  )}

                  {userTemplateOptions.length === 0 ? (
                    <SpaceBetween size="m">
                      <Box variant="p" color="text-status-inactive">
                        No custom analysis templates found. Create one first to edit.
                      </Box>
                      <Button
                        variant="normal"
                        onClick={handleBackToMenu}
                      >
                        Back
                      </Button>
                    </SpaceBetween>
                  ) : (
                    <SpaceBetween size="m">
                      <Select
                        selectedOption={
                          createState.selectedTemplateForEdit
                            ? userTemplateOptions.find(option => option.value === createState.selectedTemplateForEdit) || null
                            : null
                        }
                        onChange={handleTemplateSelectionForEdit}
                        options={userTemplateOptions}
                        placeholder="Select an analysis template to edit"
                        filteringType="auto"
                        selectedAriaLabel="Selected"
                      />

                      {createState.selectedTemplateForEdit && (
                        <SpaceBetween size="m">
                          <div>
                            <Box variant="awsui-key-label">Name</Box>
                            <Input
                              value={createState.analysisName}
                              onChange={({ detail }) => setCreateState(prev => ({ ...prev, analysisName: detail.value }))}
                              placeholder="Analysis Name"
                              disabled={createState.isCreating}
                            />
                          </div>

                          <div>
                            <Box variant="awsui-key-label">Description</Box>
                            <Input
                              value={createState.analysisDescription}
                              onChange={({ detail }) => setCreateState(prev => ({ ...prev, analysisDescription: detail.value }))}
                              placeholder="Analysis Description"
                              disabled={createState.isCreating}
                            />
                          </div>

                          <div>
                            <Box variant="awsui-key-label">Prompt</Box>
                            <Textarea
                              value={createState.analysisPrompt}
                              onChange={({ detail }) => setCreateState(prev => ({ ...prev, analysisPrompt: detail.value }))}
                              placeholder={'Enter your analysis prompt here. Be sure to include the keyword "{transcript}" where the media transcript will be added.'}
                              rows={6}
                              disabled={createState.isCreating}
                            />
                          </div>

                          <SpaceBetween size="s" direction="horizontal">
                            <Button
                              variant="primary"
                              onClick={handleCreateAnalysis}
                              loading={createState.isCreating}
                              disabled={!createState.analysisName.trim() || !createState.analysisDescription.trim() || !createState.analysisPrompt.trim()}
                            >
                              Update Analysis
                            </Button>
                            <Button
                              variant="normal"
                              onClick={handleBackToMenu}
                              disabled={createState.isCreating}
                            >
                              Back
                            </Button>
                          </SpaceBetween>
                        </SpaceBetween>
                      )}

                      {!createState.selectedTemplateForEdit && (
                        <Button
                          variant="normal"
                          onClick={handleBackToMenu}
                        >
                          Back
                        </Button>
                      )}
                    </SpaceBetween>
                  )}
                </SpaceBetween>
              )}

              {createState.currentView === 'remove' && (
                <SpaceBetween size="m">
                  {createState.createError && (
                    <Alert type="error" dismissible onDismiss={() => setCreateState(prev => ({ ...prev, createError: null }))}>
                      {createState.createError}
                    </Alert>
                  )}

                  {userTemplateOptions.length === 0 ? (
                    <SpaceBetween size="m">
                      <Box variant="p" color="text-status-inactive">
                        No custom analysis templates found. Create one first to delete.
                      </Box>
                      <Button
                        variant="normal"
                        onClick={handleBackToMenu}
                      >
                        Back
                      </Button>
                    </SpaceBetween>
                  ) : (
                    <SpaceBetween size="m">
                      <Select
                        selectedOption={
                          createState.selectedTemplateForDelete
                            ? userTemplateOptions.find(option => option.value === createState.selectedTemplateForDelete) || null
                            : null
                        }
                        onChange={handleTemplateSelectionForDelete}
                        options={userTemplateOptions}
                        placeholder="Select an analysis template to delete"
                        filteringType="auto"
                        selectedAriaLabel="Selected"
                        disabled={createState.isDeleting}
                      />

                      <SpaceBetween size="s" direction="horizontal">
                        {createState.selectedTemplateForDelete && (
                          <Button
                            variant="primary"
                            onClick={handleDeleteAnalysis}
                            loading={createState.isDeleting}
                          >
                            Permanently Delete
                          </Button>
                        )}
                        <Button
                          variant="normal"
                          onClick={handleBackToMenu}
                          disabled={createState.isDeleting}
                        >
                          Back
                        </Button>
                      </SpaceBetween>
                    </SpaceBetween>
                  )}
                </SpaceBetween>
              )}
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
