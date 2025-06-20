// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React from 'react';
import {
  Container,
  Header,
  Box,
  Spinner,
  Alert,
  Textarea
} from '@cloudscape-design/components';
import { AnalysisResultsProps } from '../types/analysis';

/**
 * Component for displaying analysis results in a scrollable container
 * Mimics the functionality of the Streamlit scrollableTextbox component
 */
export const AnalysisResults: React.FC<AnalysisResultsProps> = ({
  result,
  isLoading,
  error
}) => {
  if (error) {
    return (
      <Container header={<Header variant="h2">Analysis Results</Header>}>
        <Alert type="error" header="Analysis Error">
          {error}
        </Alert>
      </Container>
    );
  }

  if (isLoading) {
    return (
      <Container header={<Header variant="h2">Analysis Results</Header>}>
        <Box textAlign="center" padding="l">
          <Spinner size="large" />
          <Box variant="p" padding={{ top: "s" }}>
            Running analysis... This may take a few moments.
          </Box>
        </Box>
      </Container>
    );
  }

  if (!result) {
    return (
      <Container header={<Header variant="h2">Analysis Results</Header>}>
        <Box variant="p" color="text-status-inactive">
          Analysis results will be displayed here when complete.
        </Box>
      </Container>
    );
  }

  return (
    <Container header={<Header variant="h2">Analysis Results</Header>}>
      <Textarea
        value={result}
        readOnly
        rows={15}
        placeholder="Analysis results will appear here..."
        spellcheck={false}
      />
    </Container>
  );
};

export default AnalysisResults;
