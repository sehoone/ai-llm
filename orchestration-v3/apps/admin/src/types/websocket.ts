export type WebSocketMessageType = 'text' | 'audio' | 'reset' | 'evaluate';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  text?: string;
  audio?: string;
  audio_data?: string;
  format?: string;
}

