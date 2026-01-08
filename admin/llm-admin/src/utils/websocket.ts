import { WebSocketMessage } from '@/types/websocket';
import { ConversationResponse } from '@/types/conversation';

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  constructor(url?: string) {
    let baseUrl: string;
    if (url) {
      baseUrl = url;
    } else if (process.env.NEXT_PUBLIC_WS_URL) {
      baseUrl = process.env.NEXT_PUBLIC_WS_URL;
    } else {
      // 현재 페이지의 프로토콜에 따라 ws:// 또는 wss:// 사용
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // nginx를 통해 프록시되므로 같은 호스트와 포트 사용
      baseUrl = `${protocol}//${window.location.host}/ws/conversation`;
    }
    
    // URL에 경로가 없으면 /ws/conversation 추가
    this.url = baseUrl.endsWith('/ws/conversation') 
      ? baseUrl 
      : baseUrl.replace(/\/$/, '') + '/ws/conversation';
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        let resolved = false;

        this.ws.onopen = () => {
          console.log('WebSocket 연결됨:', this.url);
          this.reconnectAttempts = 0;
          this.emit('open', {});
          if (!resolved) {
            resolved = true;
            resolve();
          }
        };

        this.ws.onmessage = (event) => {
          try {
            const data: ConversationResponse = JSON.parse(event.data);
            this.emit('message', data);
          } catch (error) {
            console.error('메시지 파싱 오류:', error);
            this.emit('error', { error: '메시지 파싱 실패' });
          }
        };

        this.ws.onerror = (error) => {
          // 초기 연결 실패 시에는 조용히 처리하고 재연결 시도
          // (onclose에서 attemptReconnect가 호출됨)
          // 첫 연결 시도가 아닌 경우에만 경고 표시
          if (this.reconnectAttempts > 0) {
            console.warn('WebSocket 연결 오류:', this.url);
          }
          // reject는 하지 않음 - onclose에서 재연결 시도
        };

        this.ws.onclose = (event) => {
          if (event.code !== 1000) {
            // 정상 종료가 아닌 경우
            console.log('WebSocket 연결 종료 (재연결 시도)', event.code);
          } else {
            console.log('WebSocket 연결 종료');
          }
          this.emit('close', {});
          
          // 연결이 성공하지 못한 경우 (첫 연결 실패)
          if (!resolved) {
            resolved = true;
            // reject하지 않고 조용히 처리 - 재연결 시도
            this.attemptReconnect();
          } else {
            // 이미 연결되었던 경우 재연결 시도
            this.attemptReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`재연결 시도 ${this.reconnectAttempts}/${this.maxReconnectAttempts} (${this.url})`);
        this.connect().catch((err) => {
          // 재연결 실패는 onclose에서 다시 attemptReconnect가 호출됨
          console.warn('재연결 실패:', err.message);
        });
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      const errorMessage = `백엔드 서버에 연결할 수 없습니다 (${this.url}). 서버가 실행 중인지 확인하세요.`;
      console.error(errorMessage);
      this.emit('error', { error: errorMessage });
    }
  }

  send(message: WebSocketMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket이 연결되지 않았습니다.');
      this.emit('error', { error: 'WebSocket이 연결되지 않았습니다.' });
    }
  }

  sendText(text: string) {
    this.send({ type: 'text', text });
  }

  sendAudio(audioData: string, format: string = 'wav') {
    this.send({ type: 'audio', audio_data: audioData, format });
  }

  reset() {
    this.send({ type: 'reset' });
  }

  evaluate() {
    this.send({ type: 'evaluate' });
  }

  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  off(event: string, callback: (data: any) => void) {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(callback);
    }
  }

  private emit(event: string, data: any) {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach((callback) => callback(data));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

