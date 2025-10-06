import { FullQAnswer, ChatMessage } from '../types/chat';
import { Amplify } from 'aws-amplify';

// WebSocket message size limit for API Gateway (32KB)
const CHUNK_SIZE = 32 * 1024;

// WebSocket message steps
enum WebSocketStep {
  START = 'START',
  BODY = 'BODY',
  END = 'END'
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
export class ChatWebSocketService {
  private ws: WebSocket | null = null;
  private wsUrl: string;
  private receivedCount: number = 0;
  private expectedChunks: number = 0;

  constructor() {
    // Try to get WebSocket URL from configuration
    try {
      this.wsUrl = this.getWebSocketUrl();
      console.log('Got this.wsUrl = ',this.wsUrl)
    } catch (error) {
      console.error('Failed to initialize WebSocket service:', error);
      throw error;
    }
  }

  private getWebSocketUrl(): string {
    // Always prioritize Amplify configuration over environment variables
    try {
      const config = Amplify.getConfig() as any;
      if (config?.WebSocket?.endpoint) {
        console.log('Using WebSocket URL from Amplify configuration:', config.WebSocket.endpoint);
        return config.WebSocket.endpoint;
      }
    } catch (error) {
      console.warn('Could not load WebSocket URL from Amplify configuration:', error);
    }

    // Only use environment variable as fallback for local development
    // @ts-ignore - Vite handles this at build time
    const envUrl = import.meta.env?.VITE_WS_API_URL;
    if (envUrl && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
      console.log('Using WebSocket URL from environment variable (local development):', envUrl);
      return envUrl;
    }

    // No hardcoded fallback - throw an error instead
    throw new Error(
      'WebSocket URL not configured. Please ensure aws-exports.json contains WebSocket.endpoint'
    );
  }

  async connect(authToken: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Clean token (remove Bearer prefix if present)
        const cleanToken = authToken.startsWith('Bearer ') ? authToken.substring(7) : authToken;
        
        console.log('🔌 Attempting WebSocket connection to:', this.wsUrl);
        console.log('🔑 Auth token length:', cleanToken.length);
        
        // Connect without auth in URL - auth moved to message body
        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
          console.log('🔗 WebSocket TCP connection established (onopen fired)');
          console.log('📤 Sending START message to authenticate with API Gateway...');
          // Send START message with token for authentication
          this.sendStartMessage(cleanToken)
            .then(() => {
              console.log('✅ WebSocket connection fully established and authenticated');
              resolve();
            })
            .catch((error) => {
              console.error('❌ WebSocket authentication failed:', error);
              reject(error);
            });
        };

        this.ws.onerror = (error) => {
          console.error('❌ WebSocket TCP connection error:', error);
          reject(new Error('WebSocket TCP connection failed'));
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
        console.error('❌ Cannot send START message: WebSocket TCP connection not open (readyState:', this.ws?.readyState, ')');
        reject(new Error('WebSocket TCP connection is not open'));
        return;
      }

      const startMessage: StartMessage = {
        step: WebSocketStep.START,
        token: token
      };

      // Set up one-time message listener for START response
      const handleStartResponse = (event: MessageEvent) => {
        this.ws!.removeEventListener('message', handleStartResponse);
        
        console.log('📥 Received START response from API Gateway:', event.data);
        
        if (event.data === 'Session started.') {
          console.log('✅ API Gateway authentication successful - session started');
          resolve();
        } else {
          console.error('❌ API Gateway authentication failed:', event.data);
          reject(new Error(`API Gateway authentication failed: ${event.data}`));
        }
      };

      this.ws.addEventListener('message', handleStartResponse);
      
      console.log('📤 Sending START message to API Gateway with auth token...');
      this.ws.send(JSON.stringify(startMessage));
      console.log('📤 START message sent via WebSocket (waiting for API Gateway response)');
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
        if (message === 'Message sent.' || message === 'Streaming started' || message.trim() === '') {
          console.log('✅ Message processing completed or started');
          continue; // Continue waiting for actual streaming responses
        }

        let parsedResponse;
        try {
          parsedResponse = JSON.parse(message);
        } catch (parseError) {
          // Log first occurrence of parse error with more detail
          console.warn('JSON parse failed, skipping message. First 200 chars:', message.substring(0, 200));
          continue;
        }

        // Check for completion status
        if (parsedResponse.status === 'COMPLETE') {
          console.log('✅ Streaming completed');
          break;
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
            console.log('📚 Citations:', latestAnswer.citations.map((c: any) => 
              `${c.media_name} @ ${c.timestamp}s`
            ).join(', '));
          }
        }

        // Yield the parsed FullQAnswer
        yield parsedResponse as FullQAnswer;

      } catch (error) {
        console.error('Unexpected error in response generator:', error);
        // Continue streaming even on unexpected errors
        continue;
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

// Use a lazy singleton pattern instead of initializing immediately
let _instance: ChatWebSocketService | null = null;

export const chatWebSocketService = {
  getInstance(): ChatWebSocketService {
    if (!_instance) {
      try {
        _instance = new ChatWebSocketService();
      } catch (error) {
        console.warn('WebSocket service initialization deferred until configuration is loaded');
        // Return a temporary instance that will be replaced on the next call
        // after configuration is loaded
        return {
          connect: async () => {
            _instance = new ChatWebSocketService();
            return _instance.connect(arguments[0]);
          },
          sendMessage: async () => {
            _instance = new ChatWebSocketService();
            return _instance.sendMessage(
              arguments[0], 
              arguments[1], 
              arguments[2], 
              arguments[3], 
              arguments[4]
            );
          },
          disconnect: () => {}
        } as unknown as ChatWebSocketService;
      }
    }
    return _instance;
  },
  
  connect(token: string): Promise<void> {
    return this.getInstance().connect(token);
  },
  
  sendMessage(
    messages: ChatMessage[],
    username: string,
    token: string,
    mediaNames: string[] = [],
    transcriptJobId?: string
  ): Promise<AsyncGenerator<FullQAnswer, void, unknown>> {
    return this.getInstance().sendMessage(messages, username, token, mediaNames, transcriptJobId);
  },
  
  disconnect(): void {
    if (_instance) {
      _instance.disconnect();
    }
  }
};
