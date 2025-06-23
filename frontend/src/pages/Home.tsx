// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React from 'react';
import {
  ContentLayout,
  Header,
  SpaceBetween,
  Box,
  Button,
  Grid,
  Container,
  Icon,
  Link,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import BaseAppLayout from '../components/base-app-layout';
import '../styles/app.scss';

const HomePage: React.FC = () => {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate('/file-management'); // Navigate to File Management page
  };

  const handleChatWithMedia = () => {
    navigate('/chat-with-media');
  };

  const handleAnalyzeMedia = () => {
    navigate('/analyze');
  };

  return (
    <BaseAppLayout
      content={
        <ContentLayout
          header={
            <Box textAlign="center">
              <Header
                variant="h1"
              >
                Welcome to <span style={{ color: "#F98125" }}>ReVIEW</span>
              </Header>
            </Box>
          }
        >
          <SpaceBetween size="xl">
            {/* Main Introduction */}
            <Container>
              <div className="hero-background">
                {/* Overlay for better text readability */}
                <div className="hero-overlay" />
                
                {/* Content */}
                <div className="hero-content">
                  <SpaceBetween size="m">
                    <Box textAlign="center">
                      <Box variant="h1" padding={{ bottom: "s" }}>
                        <span style={{ color: "#F98125", fontWeight: "bold" }}>Re</span><span style={{ color: "white" }}>corded </span><span style={{ color: "#F98125", fontWeight: "bold" }}>V</span><span style={{ color: "white" }}>oice </span><span style={{ color: "#F98125", fontWeight: "bold" }}>I</span><span style={{ color: "white" }}>nsight </span><span style={{ color: "#F98125", fontWeight: "bold" }}>E</span><span style={{ color: "white" }}>xtraction </span><span style={{ color: "#F98125", fontWeight: "bold" }}>W</span><span style={{ color: "white" }}>ebapp</span>
                      </Box>
                      <div style={{ color: "rgba(255, 255, 255, 0.9)", fontSize: "1.125rem", fontWeight: "400", lineHeight: "1.4" }}>
                        Transform your audio and video recordings into actionable insights using AI
                      </div>
                    </Box>

                    <Box textAlign="center">
                      <Button
                        variant="primary"
                        onClick={handleGetStarted}
                        iconName="upload"
                        className="hero-cta-button"
                      >
                        Get Started - Upload Files
                      </Button>
                    </Box>
                  </SpaceBetween>
                </div>
              </div>
            </Container>

            {/* Feature Overview */}
            <div style={{ 
              display: "grid", 
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", 
              gap: "16px",
              alignItems: "stretch"
            }}>
              {/* File Management */}
              <Container>
                <div style={{ 
                  height: "100%", 
                  minHeight: "260px",
                  display: "flex", 
                  flexDirection: "column", 
                  justifyContent: "space-between" 
                }}>
                  <SpaceBetween size="m">
                  <Box textAlign="center">
                    <Icon name="folder" size="large" />
                  </Box>
                  <Box variant="h3" textAlign="center">
                    File Management
                  </Box>
                  <Box variant="p" textAlign="center" color="text-body-secondary">
                    Upload audio and video files for automatic processing. 
                    Monitor status and manage your media library.
                  </Box>
                  <Box textAlign="center">
                    <Button
                      variant="normal"
                      onClick={handleGetStarted}
                      iconName="external"
                    >
                      Manage Files
                    </Button>
                  </Box>
                  </SpaceBetween>
                </div>
              </Container>

              {/* Chat with Media */}
              <Container>
                <div style={{ 
                  height: "100%", 
                  minHeight: "260px",
                  display: "flex", 
                  flexDirection: "column", 
                  justifyContent: "space-between" 
                }}>
                  <SpaceBetween size="m">
                  <Box textAlign="center">
                    <Icon name="contact" size="large" />
                  </Box>
                  <Box variant="h3" textAlign="center">
                    Chat with Your Media
                  </Box>
                  <Box variant="p" textAlign="center" color="text-body-secondary">
                    Ask questions in any language about your recordings and get AI-powered answers 
                    with clickable citations that jump to exact timestamps.
                  </Box>
                  <Box textAlign="center">
                    <Button
                      variant="normal"
                      onClick={handleChatWithMedia}
                      iconName="external"
                    >
                      Start Chatting
                    </Button>
                  </Box>
                  </SpaceBetween>
                </div>
              </Container>

              {/* Analyze Media */}
              <Container>
                <div style={{ 
                  height: "100%", 
                  minHeight: "260px",
                  display: "flex", 
                  flexDirection: "column", 
                  justifyContent: "space-between" 
                }}>
                  <SpaceBetween size="m">
                  <Box textAlign="center">
                    <Icon name="search" size="large" />
                  </Box>
                  <Box variant="h3" textAlign="center">
                    Analyze Your Media
                  </Box>
                  <Box variant="p" textAlign="center" color="text-body-secondary">
                    Generate summaries, extract key topics, identify action items, 
                    and create custom analysis reports from your content.
                  </Box>
                  <Box textAlign="center">
                    <Button
                      variant="normal"
                      onClick={handleAnalyzeMedia}
                      iconName="external"
                    >
                      Analyze Content
                    </Button>
                  </Box>
                  </SpaceBetween>
                </div>
              </Container>
            </div>

            {/* Quick Start Guide */}
            <Container
              header={
                <Header variant="h2">
                  Quick Start Guide
                </Header>
              }
            >
              <SpaceBetween size="m">
                <Grid
                  gridDefinition={[
                    { colspan: { default: 12, s: 6 } },
                    { colspan: { default: 12, s: 6 } }
                  ]}
                >
                  <Box>
                    <SpaceBetween size="s">
                      <Box variant="h4">
                        <Icon name="status-positive" /> Step 1: Upload Your Files
                      </Box>
                      <Box variant="p" color="text-body-secondary">
                        Start by uploading your audio or video recordings. Files are automatically 
                        processed for AI analysis.
                      </Box>
                    </SpaceBetween>
                  </Box>

                  <Box>
                    <SpaceBetween size="s">
                      <Box variant="h4">
                        <Icon name="status-positive" /> Step 2: Explore Your Content
                      </Box>
                      <Box variant="p" color="text-body-secondary">
                        Once processed, chat with your media to ask specific questions or 
                        run analysis templates to generate insights and summaries.
                      </Box>
                    </SpaceBetween>
                  </Box>
                </Grid>
              </SpaceBetween>
            </Container>

            {/* Footer Info */}
            <Box textAlign="center" padding={{ top: "l" }}>
              <Box variant="small" color="text-body-secondary">
                Need help? Check out the{' '}
                <Link
                  href="https://github.com/aws-samples/recorded-voice-insight-extraction-webapp"
                  external
                >
                  documentation
                </Link>{' '}
                for detailed guides and examples.
              </Box>
            </Box>
          </SpaceBetween>
        </ContentLayout>
      }
    />
  );
};

export default HomePage;
