// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { fetchAuthSession } from 'aws-amplify/auth';
import axios, { AxiosResponse } from 'axios';

// Configuration state
let apiEndpoint = '';
let configLoaded = false;

// Load configuration from aws-exports.json
const loadConfig = async (): Promise<string> => {
  if (configLoaded && apiEndpoint) {
    return apiEndpoint;
  }

  try {
    const response = await fetch('/aws-exports.json');
    const config = await response.json();
    let endpoint = config.API?.REST?.endpoint || '';
    
    // Remove trailing slash if present
    if (endpoint.endsWith('/')) {
      endpoint = endpoint.slice(0, -1);
    }
    
    apiEndpoint = endpoint;
    configLoaded = true;
    console.log('API endpoint loaded:', apiEndpoint);
    return apiEndpoint;
  } catch (error) {
    console.error('Failed to load API configuration:', error);
    throw new Error('Failed to load API configuration');
  }
};

/**
 * Create axios instance with dynamic base URL
 */
const createApiInstance = async () => {
  const baseURL = await loadConfig();
  
  const api = axios.create({
    baseURL,
  });

  // HTTP Request Preprocessing
  api.interceptors.request.use(async (config) => {
    // If Authenticated, append ID Token to Request Header
    try {
      const session = await fetchAuthSession();
      const idToken = session.tokens?.idToken;
      if (idToken) {
        config.headers['Authorization'] = 'Bearer ' + idToken.toString();
      }
    } catch (error) {
      console.warn('Failed to get auth session:', error);
    }
    
    config.headers['Content-Type'] = 'application/json';
    return config;
  });

  return api;
};

/**
 * Hooks for Http Request following the reference architecture pattern
 */
const useHttp = () => {
  return {
    /**
     * GET Request (one-time)
     */
    getOnce: async <RES = any, DATA = any>(
      url: string,
      params?: DATA,
      errorProcess?: (err: any) => void
    ): Promise<AxiosResponse<RES>> => {
      try {
        const api = await createApiInstance();
        const response = await api.get<RES, AxiosResponse<RES>, DATA>(url, { params });
        return response;
      } catch (err) {
        if (errorProcess) {
          errorProcess(err);
        } else {
          console.error('API Error:', err);
        }
        throw err;
      }
    },

    /**
     * POST Request
     */
    post: async <RES = any, DATA = any>(
      url: string,
      data: DATA,
      errorProcess?: (err: any) => void
    ): Promise<AxiosResponse<RES>> => {
      try {
        const api = await createApiInstance();
        const response = await api.post<RES, AxiosResponse<RES>, DATA>(url, data);
        return response;
      } catch (err) {
        if (errorProcess) {
          errorProcess(err);
        } else {
          console.error('API Error:', err);
        }
        throw err;
      }
    },

    /**
     * PUT Request
     */
    put: async <RES = any, DATA = any>(
      url: string,
      data: DATA,
      errorProcess?: (err: any) => void
    ): Promise<AxiosResponse<RES>> => {
      try {
        const api = await createApiInstance();
        const response = await api.put<RES, AxiosResponse<RES>, DATA>(url, data);
        return response;
      } catch (err) {
        if (errorProcess) {
          errorProcess(err);
        } else {
          console.error('API Error:', err);
        }
        throw err;
      }
    },

    /**
     * DELETE Request
     */
    delete: async <RES = any, DATA = any>(
      url: string,
      params?: DATA,
      errorProcess?: (err: any) => void
    ): Promise<AxiosResponse<RES>> => {
      try {
        const api = await createApiInstance();
        const response = await api.delete<RES, AxiosResponse<RES>, DATA>(url, { params });
        return response;
      } catch (err) {
        if (errorProcess) {
          errorProcess(err);
        } else {
          console.error('API Error:', err);
        }
        throw err;
      }
    },

    /**
     * PATCH Request
     */
    patch: async <RES = any, DATA = any>(
      url: string,
      data: DATA,
      errorProcess?: (err: any) => void
    ): Promise<AxiosResponse<RES>> => {
      try {
        const api = await createApiInstance();
        const response = await api.patch<RES, AxiosResponse<RES>, DATA>(url, data);
        return response;
      } catch (err) {
        if (errorProcess) {
          errorProcess(err);
        } else {
          console.error('API Error:', err);
        }
        throw err;
      }
    },
  };
};

export default useHttp;
