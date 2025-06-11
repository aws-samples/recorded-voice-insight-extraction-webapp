import { JobData } from '../types/chat';

export const retrieveAllItems = async (
  username: string,
  authToken: string,
  maxRows?: number
): Promise<JobData[]> => {
  try {
    const response = await fetch('/api/ddb', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authToken,
      },
      body: JSON.stringify({
        action: 'retrieve_all_items',
        username,
        max_rows: maxRows,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching items:', error);
    throw error;
  }
};
