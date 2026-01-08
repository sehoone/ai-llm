'use client';

import { useAudioRecorder } from '@/hooks/audio/useAudioRecorder';
import { useEffect } from 'react';

interface AudioRecorderProps {
  onRecordingComplete: (audioBase64: string) => void;
  disabled?: boolean;
}

export default function AudioRecorder({ onRecordingComplete, disabled }: AudioRecorderProps) {
  const {
    isRecording,
    audioBlob,
    error,
    startRecording,
    stopRecording,
    convertToBase64,
    clearAudio,
  } = useAudioRecorder();

  useEffect(() => {
    if (audioBlob) {
      convertToBase64(audioBlob).then((base64) => {
        onRecordingComplete(base64);
        clearAudio();
      });
    }
  }, [audioBlob, convertToBase64, onRecordingComplete, clearAudio]);

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        onClick={isRecording ? stopRecording : startRecording}
        disabled={disabled}
        className={`
          px-6 py-3 rounded-full font-semibold text-white transition-all duration-200
          ${isRecording
            ? 'bg-red-500 hover:bg-red-600 animate-pulse'
            : 'bg-sky-600 hover:bg-sky-700'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          shadow-lg hover:shadow-xl
        `}
      >
        {isRecording ? (
          <span className="flex items-center gap-2">
            <span className="w-3 h-3 bg-white rounded-full animate-pulse"></span>
            녹음 중...
          </span>
        ) : (
          <span className="flex items-center gap-2">
            <svg
              className="w-5 h-5"
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
            녹음 시작
          </span>
        )}
      </button>
      {error && (
        <p className="text-sm text-red-500 mt-1">{error}</p>
      )}
    </div>
  );
}

