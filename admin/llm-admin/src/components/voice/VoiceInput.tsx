'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAudioCaptureWithSTT } from '@/hooks/audio/useAudioCaptureWithSTT';
import { logger } from '@/lib/logger';

interface VoiceInputProps {
  onSpeechResult: (text: string) => void;
  onAudioData: (audioBase64: string, format: string) => void;
  disabled?: boolean;
  autoStart?: boolean;
  onRecognitionReady?: (controls: { pause: () => void; resume: () => void; stop: () => void }) => void;
  onError?: (error: string) => void;
}

export default function VoiceInput({
  onSpeechResult,
  onAudioData,
  disabled = false,
  autoStart = true,
  onRecognitionReady,
  onError,
}: VoiceInputProps) {
  const [isAutoStartPaused, setIsAutoStartPaused] = useState(false);

  const handleAudioData = (audioBase64: string) => {
    logger.debug('[VoiceInput] 오디오 데이터 수신, 길이:', audioBase64.length);
    // Send audio to backend via WebSocket with type: "audio"
    onAudioData(audioBase64, 'wav');
  };

  const handleUnexpectedStop = useCallback(() => {
    logger.debug('[VoiceInput] 비정상 종료 감지 - 자동 시작 일시 중지');
    setIsAutoStartPaused(true);
  }, []);

  // AI 발화가 끝나고 입력이 활성화되면 자동 시작 일시 중지 상태를 해제
  useEffect(() => {
    if (!disabled) {
       
      setIsAutoStartPaused(false);
    }
  }, [disabled]);

  const { isListening, isSupported, error, startListening, stopListening, pauseListening, resumeListening } =
    useAudioCaptureWithSTT(handleAudioData, onSpeechResult, onError, handleUnexpectedStop);

  useEffect(() => {
    if (onRecognitionReady) {
      onRecognitionReady({
        pause: pauseListening,
        resume: resumeListening,
        stop: stopListening,
      });
    }
  }, [onRecognitionReady, pauseListening, resumeListening, stopListening]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    
    // isAutoStartPaused가 true이면 자동 시작하지 않음
    if (autoStart && !disabled && isSupported && !isListening && !isAutoStartPaused) {
      // 상태 변경 시 약간의 딜레이를 두어 불필요한 시작 방지 (예: AI 응답 직전)
      timer = setTimeout(() => {
        startListening();
      }, 500);
    } else if (disabled && isListening) {
      stopListening();
    }
    
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [autoStart, disabled, isSupported, isListening, startListening, stopListening, isAutoStartPaused]);

  // Auto start listening when component mounts and exam starts
  useEffect(() => {
    if (autoStart && !disabled && isSupported && !isAutoStartPaused) {
      // 약간의 딜레이 후 시작
      const timer = setTimeout(() => {
        if (!isListening) {
          startListening();
        }
      }, 300);
      return () => clearTimeout(timer);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleToggle = () => {
    if (isListening) {
      stopListening();
    } else {
      // 사용자가 수동으로 시작하면 자동 시작 일시 중지 해제
      setIsAutoStartPaused(false);
      startListening();
    }
  };

  if (!isSupported) {
    return (
      <div className="flex flex-col items-center gap-2">
        <div className="px-6 py-3 rounded-full bg-gray-400 text-white">
          음성 인식을 지원하지 않는 브라우저입니다
        </div>
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative">
        <button
          onClick={handleToggle}
          disabled={disabled}
          className={`
            w-20 h-20 rounded-full font-semibold text-white transition-all duration-200
            flex items-center justify-center
            ${isListening
              ? 'bg-red-500 hover:bg-red-600 animate-pulse'
              : isAutoStartPaused
                ? 'bg-orange-500 hover:bg-orange-600'
                : 'bg-sky-600 hover:bg-sky-700'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            shadow-lg hover:shadow-xl
          `}
        >
          {isListening ? (
            <svg
              className="w-8 h-8"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
            </svg>
          ) : isAutoStartPaused ? (
            <svg 
              className="w-8 h-8" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <svg
              className="w-8 h-8"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          )}
        </button>
        {isListening && (
          <div className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-75"></div>
        )}
      </div>
      <div className="text-center min-h-[40px] flex flex-col justify-center">
        {isListening ? (
          <p className="text-sm text-red-600 font-medium animate-pulse">듣는 중... 말씀해주세요</p>
        ) : isAutoStartPaused ? (
          <>
            <p className="text-sm text-orange-600 font-bold">음성 인식 일시정지</p>
            <p className="text-xs text-gray-500">버튼을 눌러 다시 시작하세요</p>
          </>
        ) : disabled ? (
          <p className="text-sm text-gray-500">AI가 답변 중입니다...</p>
        ) : (
          <p className="text-sm text-gray-500">준비 중...</p>
        )}
      </div>
      {error && <p className="text-sm text-red-500 mt-1">{error}</p>}
    </div>
  );
}

