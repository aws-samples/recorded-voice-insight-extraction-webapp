const API_BASE_URL = '/api';

export const retrieveTranscriptByJobId = async (
  jobId: string,
  username: string,
  authToken: string
): Promise<string> => {
  const response = await fetch(`${API_BASE_URL}/s3/transcript/${jobId}`, {
    method: 'GET',
    headers: {
      'Authorization': authToken,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to retrieve transcript: ${response.status} ${response.statusText}`);
  }

  return response.text();
};
