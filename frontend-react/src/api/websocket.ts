import { FullQAnswer, ChatMessage } from '../types/chat';

// WebSocket message size limit for API Gateway (32KB)
const CHUNK_SIZE = 32 * 1024;

// WebSocket message steps
enum WebSocketStep {
  START = 'START',
  BODY = 'BODY',
  END = 'END'
}

// Error class for WebSocket timeouts
export class WebSocketTimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'WebSocketTimeoutError';
  }
}

// Interface for chat input message
interface ChatInput {
  messages: string;
  username: string;
  media_names?: string;
  transcript_job_id?: string;
}

// Interface for START message
interface StartMessage {
  step: WebSocketStep.START;
  token: string;
}

// Interface for BODY message
interface BodyMessage {
  step: WebSocketStep.BODY;
  index: number;
  part: string;
}

// Interface for END message
interface EndMessage {
  step: WebSocketStep.END;
  token: string;
}

// Remove unused WebSocketMessage type since we have specific types
// type WebSocketMessage = StartMessage | BodyMessage | EndMessage;
export class ChatWebSocketService {
  private ws: WebSocket | null = null;
  private wsUrl: string;
  private receivedCount: number = 0;
  private expectedChunks: number = 0;

  constructor() {
    // Use environment variable or fallback URL
    // @ts-ignore - Vite handles this at build time
    this.wsUrl = import.meta.env?.VITE_WS_API_URL || 'wss://qabuyr9e0i.execute-api.us-east-1.amazonaws.com/prod';
  }

  async connect(authToken: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Clean token (remove Bearer prefix if present)
        const cleanToken = authToken.startsWith('Bearer ') ? authToken.substring(7) : authToken;
        
        console.log('Connecting to WebSocket:', this.wsUrl);
        console.log('Token length:', cleanToken.length);
        
        // Connect without auth in URL - auth moved to message body
        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
          console.log('WebSocket connected successfully');
          // Send START message with token for authentication
          this.sendStartMessage(cleanToken)
            .then(() => resolve())
            .catch(reject);
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(new Error('WebSocket connection failed'));
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          if (event.code === 1006) {
            console.error('WebSocket closed abnormally - likely network issue');
          }
        };

      } catch (error) {
        console.error('Error creating WebSocket:', error);
        reject(error);
      }
    });
  }

  private async sendStartMessage(token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket is not connected'));
        return;
      }

      const startMessage: StartMessage = {
        step: WebSocketStep.START,
        token: token
      };

      // Set up one-time message listener for START response
      const handleStartResponse = (event: MessageEvent) => {
        this.ws!.removeEventListener('message', handleStartResponse);
        
        if (event.data === 'Session started.') {
          console.log('✅ Authentication successful - session started');
          resolve();
        } else {
          console.error('❌ Authentication failed:', event.data);
          reject(new Error(`Authentication failed: ${event.data}`));
        }
      };

      this.ws.addEventListener('message', handleStartResponse);
      this.ws.send(JSON.stringify(startMessage));
      console.log('📤 Sent START message with authentication token');
    });
  }
  private async sendChunkedMessage(chatInput: ChatInput, token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket is not connected'));
        return;
      }

      // Convert chat input to string
      const payloadString = JSON.stringify(chatInput);
      
      // Split into chunks
      const chunks: string[] = [];
      const chunkCount = Math.ceil(payloadString.length / CHUNK_SIZE);
      
      for (let i = 0; i < chunkCount; i++) {
        const start = i * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, payloadString.length);
        chunks.push(payloadString.substring(start, end));
      }

      console.log(`📦 Splitting message into ${chunks.length} chunks`);
      
      this.receivedCount = 0;
      this.expectedChunks = chunks.length;

      // Set up message listener for chunk acknowledgments
      const handleChunkResponse = (event: MessageEvent) => {
        if (event.data === 'Message part received.') {
          this.receivedCount++;
          console.log(`✅ Chunk ${this.receivedCount}/${this.expectedChunks} acknowledged`);
          
          if (this.receivedCount === this.expectedChunks) {
            // All chunks sent, now send END message
            this.ws!.removeEventListener('message', handleChunkResponse);
            this.sendEndMessage(token)
              .then(() => resolve())
              .catch(reject);
          }
        } else {
          this.ws!.removeEventListener('message', handleChunkResponse);
          reject(new Error(`Unexpected chunk response: ${event.data}`));
        }
      };

      this.ws.addEventListener('message', handleChunkResponse);

      // Send all chunks
      chunks.forEach((chunk, index) => {
        const bodyMessage: BodyMessage = {
          step: WebSocketStep.BODY,
          index: index,
          part: chunk
        };
        
        this.ws!.send(JSON.stringify(bodyMessage));
        console.log(`📤 Sent chunk ${index + 1}/${chunks.length}`);
      });
    });
  }

  private async sendEndMessage(token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket is not connected'));
        return;
      }

      const endMessage: EndMessage = {
        step: WebSocketStep.END,
        token: token
      };

      this.ws.send(JSON.stringify(endMessage));
      console.log('📤 Sent END message - starting to receive responses');
      resolve();
    });
  }
  async sendMessage(
    messages: ChatMessage[],
    username: string,
    token: string,
    mediaNames: string[] = [],
    transcriptJobId?: string
  ): Promise<AsyncGenerator<FullQAnswer, void, unknown>> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }

    // Clean messages similar to the Python implementation
    const cleanedMessages = this.cleanMessages(messages);

    // Prepare chat input
    const chatInput: ChatInput = {
      messages: JSON.stringify(cleanedMessages),
      username,
    };

    // Add media_names if provided
    if (mediaNames.length > 0) {
      chatInput.media_names = JSON.stringify(mediaNames);
      console.log(`📁 Selected media files: ${mediaNames.join(', ')}`);
    }

    // Add transcript_job_id for single file queries
    if (transcriptJobId) {
      chatInput.transcript_job_id = transcriptJobId;
      console.log(`🔑 Using transcript job ID: ${transcriptJobId}`);
    } else {
      console.log('ℹ️ No transcript job ID provided (using RAG over all files)');
    }

    // Send message using chunked protocol
    await this.sendChunkedMessage(chatInput, token);

    // Return generator for streaming responses
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
        // Handle completion messages that aren't JSON
        if (message === 'Message sent.' || message.trim() === '') {
          console.log('✅ Message processing completed');
          break;
        }

        const parsedResponse = JSON.parse(message);

        // Check for timeout error
        if (parsedResponse.message === 'Endpoint request timed out') {
          throw new WebSocketTimeoutError('Endpoint request timed out');
        }

        // Check for error status
        if (parsedResponse.status === 'ERROR') {
          console.error('❌ Server error:', parsedResponse.reason);
          throw new Error(parsedResponse.reason || 'Unknown error from server');
        }

        // Log successful response
        if (parsedResponse.answer && parsedResponse.answer.length > 0) {
          const latestAnswer = parsedResponse.answer[parsedResponse.answer.length - 1];
          if (latestAnswer.citations && latestAnswer.citations.length > 0) {
            console.log('📚 Citations:', latestAnswer.citations.map(c => 
              `${c.media_name} @ ${c.timestamp}s`
            ).join(', '));
          }
        }

        // Yield the parsed FullQAnswer
        yield parsedResponse as FullQAnswer;

      } catch (error) {
        if (error instanceof WebSocketTimeoutError) {
          throw error;
        }
        
        // Handle non-JSON completion messages
        if (message === 'Message sent.' || message.trim() === '') {
          console.log('✅ Message processing completed');
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

      const handleError = (_error: Event) => {
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
