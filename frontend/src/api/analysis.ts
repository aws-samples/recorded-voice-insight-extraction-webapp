// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { 
  Job, 
  AnalysisTemplate
} from '../types/analysis';
import useHttp from '../hooks/useHttp';

/**
 * API functions for analysis operations
 */
export class AnalysisApi {
  private http = useHttp();

  /**
   * Retrieve all items for a user from DynamoDB
   */
  async retrieveAllItems(username: string, maxRows?: number): Promise<Job[]> {
    const requestBody = {
      action: 'retrieve_all_items',
      username,
      maxRows: maxRows || 100,
    };

    try {
      const response = await this.http.post<Job[]>('/ddb', requestBody);
      return response.data;
    } catch (error) {
      console.error('Error retrieving items:', error);
      throw error;
    }
  }

  /**
   * Get analysis templates
   */
  async getAnalysisTemplates(): Promise<AnalysisTemplate[]> {
    try {
      const response = await this.http.getOnce<AnalysisTemplate[]>('/analysis-templates');
      return response.data;
    } catch (error) {
      console.error('Error getting analysis templates:', error);
      throw error;
    }
  }

  /**
   * Submit analysis request
   */
  async submitAnalysis(
    username: string,
    selectedFiles: string[],
    template: AnalysisTemplate,
    customPrompt?: string
  ): Promise<string> {
    const requestBody = {
      foundation_model_id: template.model_id,
      system_prompt: template.system_prompt,
      main_prompt: customPrompt || template.template_prompt,
      bedrock_kwargs: template.bedrock_kwargs,
      username,
      selectedFiles,
      template_id: template.template_id,
    };

    try {
      const response = await this.http.post<string>('/llm', requestBody);
      return response.data;
    } catch (error) {
      console.error('Error submitting analysis:', error);
      throw error;
    }
  }

  /**
   * Get job status
   */
  async getJobStatus(jobId: string): Promise<Job> {
    try {
      const response = await this.http.getOnce<Job>(`/job/${jobId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting job status:', error);
      throw error;
    }
  }

  /**
   * Delete job
   */
  async deleteJob(jobId: string): Promise<void> {
    try {
      await this.http.delete(`/job/${jobId}`);
    } catch (error) {
      console.error('Error deleting job:', error);
      throw error;
    }
  }

  /**
   * Get presigned URL for file download
   */
  async getPresignedUrl(key: string): Promise<{ url: string }> {
    try {
      const response = await this.http.getOnce<{ url: string }>('/s3-presigned', { key });
      return response.data;
    } catch (error) {
      console.error('Error getting presigned URL:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const analysisApi = new AnalysisApi();
