import { useState, useEffect, useCallback, useRef } from 'react';
import { WebSocketClient } from '@/utils/websocket';
import { ConversationResponse, ConversationMessage } from '@/types/conversation';
import { setGlobalAssessmentData } from '@/components/debug/PronunciationDebugPanel';

export function useWebSocket(url?: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [evaluation, setEvaluation] = useState<ConversationMessage | null>(null);
  const wsClientRef = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    const client = new WebSocketClient(url);
    wsClientRef.current = client;

    const handleOpen = () => {
      setIsConnected(true);
      setError(null);
    };

    const handleMessage = (data: ConversationResponse) => {
      if (data.error) {
        setError(data.error);
        return;
      }

      // 발음 평가 결과 처리
      if ((data as any).type === 'user_text' && (data as any).pronunciation) {
        const pronunciationData = (data as any).pronunciation;
        console.log('[디버그] 발음 평가 데이터 수신:', pronunciationData);
        
        // 발음 평가 데이터를 전역 상태에 설정
        if (pronunciationData.accuracy_score !== undefined && 
            pronunciationData.pronunciation_score !== undefined) {
          const assessmentData = {
            recognized_text: pronunciationData.recognized_text || 'N/A',
            reference_text: pronunciationData.reference_text || 'N/A',
            accuracy_score: parseFloat(pronunciationData.accuracy_score) || 0,
            pronunciation_score: parseFloat(pronunciationData.pronunciation_score) || 0,
            completeness_score: parseFloat(pronunciationData.completeness_score) || 0,
            fluency_score: parseFloat(pronunciationData.fluency_score) || 0,
            prosody_score: parseFloat(pronunciationData.prosody_score) || 0,
            word_details: pronunciationData.word_details || [],
          };
          console.log('[디버그] 평가 데이터 파싱:', assessmentData);
          setGlobalAssessmentData(assessmentData);
        }
      }

      // 사용자 텍스트 메시지 (STT 결과)
      if ((data as any).type === 'user_text' && (data as any).text) {
        const userMessage: ConversationMessage = {
          role: 'user',
          content: (data as any).text,
          timestamp: new Date(),
        };
        
        setMessages((prev) => {
          // 마지막 메시지가 로컬 메시지라면 교체, 아니면 추가
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.role === 'user' && lastMsg.isLocal) {
            return [...prev.slice(0, -1), userMessage];
          }
          return [...prev, userMessage];
        });
        return;
      }

      // 평가 결과만 있는 경우 (평가 요청 응답)
      if (!data.text && data.evaluation) {
        const evaluationMessage: ConversationMessage = {
          role: 'assistant',
          content: '',
          timestamp: new Date(),
          evaluation: data.evaluation,
        };
        setEvaluation(evaluationMessage);
        setIsLoading(false);
        return;
      }

      // AI 응답 메시지 추가 (평가 없이)
      if (data.text) {
        const aiMessage: ConversationMessage = {
          role: 'assistant',
          content: data.text,
          timestamp: new Date(),
          evaluation: undefined, // 대화 중에는 평가 없음
          audio: data.audio,
        };
        setMessages((prev) => [...prev, aiMessage]);
        setIsLoading(false);
      }
    };

    const handleError = (data: { error?: any }) => {
      setError(data.error?.message || '연결 오류가 발생했습니다.');
      setIsConnected(false);
      setIsLoading(false);
    };

    const handleClose = () => {
      setIsConnected(false);
    };

    client.on('open', handleOpen);
    client.on('message', handleMessage);
    client.on('error', handleError);
    client.on('close', handleClose);

    // 연결 시도 (초기 실패는 조용히 처리하고 재연결 시도)
    client.connect().catch((err) => {
      // 초기 연결 실패는 조용히 처리 (재연결 시도 중)
      // 최대 재연결 시도 후에만 오류 표시
      console.warn('초기 WebSocket 연결 실패 (재연결 시도 중):', err.message);
    });

    return () => {
      client.off('open', handleOpen);
      client.off('message', handleMessage);
      client.off('error', handleError);
      client.off('close', handleClose);
      client.disconnect();
    };
  }, [url]);

  const sendText = useCallback((text: string) => {
    if (!wsClientRef.current || !isConnected) {
      setError('WebSocket이 연결되지 않았습니다.');
      return;
    }

    // "모의평가 시작" 메시지는 화면에 표시하지 않음
    if (text !== '모의평가 시작') {
      // 사용자 메시지 추가
      const userMessage: ConversationMessage = {
        role: 'user',
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
    }
    
    setIsLoading(true);
    setError(null);

    wsClientRef.current.sendText(text);
  }, [isConnected]);

  const sendAudio = useCallback((audioData: string, format: string = 'wav') => {
    if (!wsClientRef.current || !isConnected) {
      setError('WebSocket이 연결되지 않았습니다.');
      return;
    }

    // 오디오 전송 중임을 표시 (STT 결과가 오면 사용자 메시지로 추가됨)
    setIsLoading(true);
    setError(null);
    wsClientRef.current.sendAudio(audioData, format);
  }, [isConnected]);

  const reset = useCallback(() => {
    if (wsClientRef.current && isConnected) {
      wsClientRef.current.reset();
      setMessages([]);
      setError(null);
      setEvaluation(null);
    }
  }, [isConnected]);

  const evaluate = useCallback(() => {
    if (!wsClientRef.current || !isConnected) {
      setError('WebSocket이 연결되지 않았습니다.');
      return;
    }

    setIsLoading(true);
    setError(null);
    wsClientRef.current.evaluate();
  }, [isConnected]);

  const addLocalMessage = useCallback((text: string) => {
    const userMessage: ConversationMessage = {
      role: 'user',
      content: text,
      timestamp: new Date(),
      isLocal: true,
    };
    setMessages((prev) => [...prev, userMessage]);
  }, []);

  return {
    isConnected,
    messages,
    error,
    isLoading,
    evaluation,
    sendText,
    sendAudio,
    reset,
    evaluate,
    addLocalMessage,
  };
}

