import { useState, useEffect, useRef, useCallback } from 'react';

interface SpeechRecognitionResult {
  [key: number]: SpeechRecognitionAlternative;
  isFinal: boolean;
  item(index: number): SpeechRecognitionAlternative;
  length: number;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionResultList {
  [key: number]: SpeechRecognitionResult;
  item(index: number): SpeechRecognitionResult;
  length: number;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: (event: SpeechRecognitionEvent) => void;
  onerror: (event: SpeechRecognitionErrorEvent) => void;
  onend: () => void;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

export function useSpeechRecognition(
  onResult: (text: string) => void,
  onError?: (error: string) => void
) {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const isListeningRef = useRef(false);
  const isPausedRef = useRef(false);
  const finalTranscriptRef = useRef<string>('');

  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  useEffect(() => {
    // 브라우저 지원 확인
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      setError('브라우저가 음성 인식을 지원하지 않습니다.');
      return;
    }

    setIsSupported(true);
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US'; // 영어 음성 인식

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      // 일시 중지 상태면 결과 무시
      if (isPausedRef.current) {
        console.log('음성 인식 일시 중지 중 - 입력 무시됨');
        return;
      }

      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results.item(i);
        if (result.isFinal) {
          const transcript = result.item(0).transcript;
          finalTranscript += transcript + ' ';
        }
      }

      if (finalTranscript) {
        const text = finalTranscript.trim();
        if (text) {
          // 최종 결과가 나오면 즉시 전송
          onResult(text);
        }
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      // console.error('음성 인식 오류:', event);
      
      // no-speech 에러는 무시하고 계속 진행
      if (event.error === 'no-speech') {
        return;
      }
      
      const errorMessage =
        event.error === 'audio-capture'
          ? '마이크에 접근할 수 없습니다.'
          : event.error === 'not-allowed'
          ? '마이크 권한이 거부되었습니다.'
          : '';
      setError(errorMessage);
      if (onError) {
        onError(errorMessage);
      }
      setIsListening(false);
    };

    recognition.onend = () => {
      // 자동으로 다시 시작 (연속 모드) - 일시중지 상태가 아닐 때만
      if (isListeningRef.current && !isPausedRef.current) {
        try {
          recognition.start();
          // 자동 재시작은 정상 동작이므로 로그 제거 (필요시 주석 해제)
          // console.log('음성 인식 자동 재시작');
        } catch (e) {
          // 재시작 중 오류는 무시 (이미 시작된 경우 등)
          // console.log('음성 인식 재시작 중 오류 (무시됨):', e);
        }
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current.abort();
      }
    };
  }, [onResult, onError]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current || !isSupported) {
      setError('음성 인식을 사용할 수 없습니다.');
      return;
    }

    // 이미 시작된 경우 무시
    if (isListeningRef.current && !isPausedRef.current) {
      console.log('음성 인식이 이미 시작되어 있음');
      return;
    }

    try {
      finalTranscriptRef.current = '';
      isPausedRef.current = false;
      setIsPaused(false);
      recognitionRef.current.start();
      setIsListening(true);
      setError(null);
      console.log('음성 인식 시작');
    } catch (err) {
      // 이미 시작된 경우의 에러는 무시
      if (err instanceof Error && err.message.includes('already started')) {
        console.log('음성 인식이 이미 시작되어 있음 (상태 동기화)');
        setIsListening(true);
        setError(null);
      } else {
        console.error('음성 인식 시작 실패:', err);
        setError('음성 인식을 시작할 수 없습니다.');
      }
    }
  }, [isSupported]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
      setIsPaused(false);
    }
  }, []);

  const pauseListening = useCallback(() => {
    if (recognitionRef.current && isListeningRef.current && !isPausedRef.current) {
      console.log('음성 인식 일시 중지 시작');
      // 먼저 플래그 설정하여 새로운 입력 차단
      isPausedRef.current = true;
      setIsPaused(true);
      
      try {
        // abort()를 사용하여 즉시 중지
        recognitionRef.current.abort();
        console.log('음성 인식 일시 중지 완료 (abort)');
      } catch (err) {
        console.error('음성 인식 일시 중지 실패:', err);
      }
    }
  }, []);

  const resumeListening = useCallback(() => {
    if (!recognitionRef.current) {
      console.log('재개 불가: recognition 객체 없음');
      return;
    }

    if (!isListeningRef.current) {
      console.log('재개 불가: 음성 인식이 시작되지 않음');
      return;
    }

    if (!isPausedRef.current) {
      console.log('재개 불가: 이미 재개된 상태');
      return;
    }

    console.log('음성 인식 재개 시작');
    // 먼저 플래그 해제
    isPausedRef.current = false;
    setIsPaused(false);
    
    try {
      recognitionRef.current.start();
      console.log('음성 인식 재개 완료');
    } catch (err) {
      console.error('음성 인식 재개 실패:', err);
      // 이미 시작된 경우 무시
      if (err instanceof Error && err.message.includes('already started')) {
        console.log('이미 시작됨 - 상태만 업데이트');
      }
    }
  }, []);

  return {
    isListening,
    isSupported,
    error,
    isPaused,
    startListening,
    stopListening,
    pauseListening,
    resumeListening,
  };
}

