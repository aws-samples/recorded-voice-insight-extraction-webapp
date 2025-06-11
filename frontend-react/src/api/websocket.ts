import { FullQAnswer, ChatMessage } from '../types/chat';

export class WebSocketTimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'WebSocketTimeoutError';
  }
}

interface WebSocketMessage {
  action: string;
  messages: string;
  username: string;
  media_names?: string;
  transcript_job_id?: string;
}

export class ChatWebSocketService {
  private ws: WebSocket | null = null;
  private wsUrl: string;

  constructor() {
    // Use environment variable or fallback to hardcoded URL
    // For local development, this should point to the actual WebSocket API Gateway URL
    this.wsUrl = import.meta.env.VITE_WS_API_URL || 'wss://qabuyr9e0i.execute-api.us-east-1.amazonaws.com/prod';
  }

  async connect(authToken: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // For browser WebSocket, we can't set headers directly
        // Pass auth token via query params (backend modified to support this for React compatibility)
        // Remove "Bearer " prefix if present since we'll pass the raw token
        const cleanToken = authToken.startsWith('Bearer ') ? authToken.substring(7) : authToken;
        const wsUrlWithAuth = `${this.wsUrl}?authorization=${cleanToken}`;
        
        console.log('Connecting to WebSocket:', this.wsUrl);
        console.log('Token length:', cleanToken.length);
        console.log('Full token:', cleanToken)
        console.log('Token starts with:', cleanToken.substring(0, 20) + '...');
        console.log('Token parts count:', cleanToken.split('.').length);
        console.log('Token parts count:', cleanToken.split('.').length);
        console.log('Full WebSocket URL (first 100 chars):', wsUrlWithAuth.substring(0, 100) + '...');
        
        this.ws = new WebSocket(wsUrlWithAuth);

        this.ws.onopen = () => {
          console.log('WebSocket connected successfully');
          resolve();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          console.error('WebSocket URL:', this.wsUrl);
          console.error('WebSocket readyState:', this.ws?.readyState);
          reject(new Error('WebSocket connection failed'));
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          if (event.code === 1006) {
            console.error('WebSocket closed abnormally - likely authentication or network issue');
          }
        };

      } catch (error) {
        console.error('Error creating WebSocket:', error);
        reject(error);
      }
    });
  }

  async sendMessage(
    messages: ChatMessage[],
    username: string,
    mediaNames: string[] = [],
    transcriptJobId?: string
  ): Promise<AsyncGenerator<FullQAnswer, void, unknown>> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }

    // Clean messages similar to the Python implementation
    const cleanedMessages = this.cleanMessages(messages);

    const messageBody: WebSocketMessage = {
      action: '$default',
      messages: JSON.stringify(cleanedMessages),
      username,
    };

    // Add media_names if provided
    if (mediaNames.length > 0) {
      messageBody.media_names = JSON.stringify(mediaNames);
    }

    // Add transcript_job_id for single file queries
    if (transcriptJobId) {
      messageBody.transcript_job_id = transcriptJobId;
    }

    this.ws.send(JSON.stringify(messageBody));

    return this.createResponseGenerator();
  }

  private cleanMessages(messages: ChatMessage[], maxMessages: number = 10): ChatMessage[] {
    // Remove citations from content (matching Python regex pattern)
    const cleanedMessages = messages.map(message => ({
      role: message.role,
      content: [{
        text: message.content[0]?.text?.replace(/\[\d+\]/g, '') || ''
      }]
    }));

    // Take last maxMessages
    const recentMessages = cleanedMessages.slice(-maxMessages);

    // Ensure first message is from user
    while (recentMessages.length > 0 && recentMessages[0].role !== 'user') {
      recentMessages.shift();
    }

    return recentMessages;
  }

  private async *createResponseGenerator(): AsyncGenerator<FullQAnswer, void, unknown> {
    if (!this.ws) {
      throw new Error('WebSocket is not connected');
    }

    while (this.ws.readyState === WebSocket.OPEN) {
      const message = await this.waitForMessage();
      
      if (!message) {
        break;
      }

      try {
        const parsedResponse = JSON.parse(message);

        // Check for timeout error
        if (parsedResponse.message === 'Endpoint request timed out') {
          throw new WebSocketTimeoutError('Endpoint request timed out');
        }

        // Yield the parsed FullQAnswer
        yield parsedResponse as FullQAnswer;

      } catch (error) {
        if (error instanceof WebSocketTimeoutError) {
          throw error;
        }
        
        if (message.trim() === '') {
          // Empty message indicates end of stream
          break;
        }
        
        console.error('Error parsing WebSocket message:', message, error);
        throw new Error(`Error parsing response: ${message}`);
      }
    }
  }

  private waitForMessage(): Promise<string | null> {
    return new Promise((resolve, reject) => {
      if (!this.ws) {
        reject(new Error('WebSocket is not connected'));
        return;
      }

      const handleMessage = (event: MessageEvent) => {
        this.ws!.removeEventListener('message', handleMessage);
        this.ws!.removeEventListener('close', handleClose);
        this.ws!.removeEventListener('error', handleError);
        resolve(event.data);
      };

      const handleClose = () => {
        this.ws!.removeEventListener('message', handleMessage);
        this.ws!.removeEventListener('close', handleClose);
        this.ws!.removeEventListener('error', handleError);
        resolve(null);
      };

      const handleError = (error: Event) => {
        this.ws!.removeEventListener('message', handleMessage);
        this.ws!.removeEventListener('close', handleClose);
        this.ws!.removeEventListener('error', handleError);
        reject(new Error('WebSocket error occurred'));
      };

      this.ws.addEventListener('message', handleMessage);
      this.ws.addEventListener('close', handleClose);
      this.ws.addEventListener('error', handleError);
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Singleton instance
export const chatWebSocketService = new ChatWebSocketService();
