import React, { useState, useEffect } from "react";
import { ContentLayout, Alert } from "@cloudscape-design/components";
import { getCurrentUser, fetchAuthSession } from "aws-amplify/auth";
import BaseAppLayout from "../components/base-app-layout";
import { AnalyzeMedia } from "./AnalyzeMedia";

const Analyze: React.FC = () => {
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const user = await getCurrentUser();
        const session = await fetchAuthSession();
        
        if (user.username && session.tokens?.idToken) {
          // Store auth info in localStorage for API calls
          localStorage.setItem('username', user.username);
          localStorage.setItem('authToken', session.tokens.idToken.toString());
          
          setIsAuthenticated(true);
        } else {
          setError("Authentication required. Please log in.");
        }
      } catch (err) {
        console.error("Authentication error:", err);
        setError("Authentication failed. Please log in.");
      }
    };

    initAuth();
  }, []);

  return (
    <BaseAppLayout
      content={
        <ContentLayout>
          {error && (
            <Alert type="error" header="Authentication Error">
              {error}
            </Alert>
          )}
          {isAuthenticated && <AnalyzeMedia />}
        </ContentLayout>
      }
    />
  );
};

export default Analyze;
