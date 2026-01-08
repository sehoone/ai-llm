import { useState, useEffect, useRef, useCallback } from 'react';

// 브라우저 내장 Web Speech API 타입 사용
// (TypeScript lib.dom.d.ts에 정의된 표준 타입)

export function useAudioCaptureWithSTT(
  onAudioData: (audioData: string) => void,
  onResult: (text: string) => void,
  onError?: (error: string) => void,
  onStop?: () => void
) {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  
  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const dataIntervalIdRef = useRef<NodeJS.Timeout | null>(null);
  
  const isListeningRef = useRef(false);
  const isPausedRef = useRef(false);
  const recognitionStartedRef = useRef(false);
  const mediaRecorderStartedRef = useRef(false);

  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  // Initialize SpeechRecognition (once only)
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      setError('브라우저가 음성 인식을 지원하지 않습니다.');
      return;
    }

    setIsSupported(true);
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      if (isPausedRef.current) {
        console.log('[STT] 일시 중지 중 - 입력 무시됨');
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
          console.log('[STT] 최종 결과:', text);
          
          // 성공적인 인식이므로 상태를 먼저 업데이트하여 onend에서 비정상 종료로 처리되지 않도록 함
          isListeningRef.current = false;
          setIsListening(false);

          // 명시적으로 중지
          if (recognition.abort) {
            try {
              recognition.abort();
              console.log('[STT] abort 호출');
            } catch (e) {
              console.log('[STT] abort 중 오류:', e);
            }
          }
          
          // MediaRecorder의 최종 데이터 요청
          if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
            console.log('[Audio] 최종 청크 요청');
            mediaRecorderRef.current.requestData?.();
            
            // 200ms 후 MediaRecorder 정지
            setTimeout(() => {
              if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                console.log('[Audio] MediaRecorder 정지');
                mediaRecorderStartedRef.current = false;
                mediaRecorderRef.current.stop();
              }
            }, 200);
          }
          
          // STT 결과 전달
          onResult(text);
        }
      }
    };

    recognition.addEventListener('start', () => {
      console.log('[STT] onstart 호출됨');
      recognitionStartedRef.current = true;
    });

    recognition.onerror = (event: any) => {
      // aborted 에러는 정상적인 중지이므로 무시
      if (event.error === 'aborted') {
        console.log('[STT] 중지됨 (정상)');
        return;
      }

      if (event.error === 'no-speech') {
        console.log('[STT] no-speech 오류 - 무시됨');
        return;
      }

      const errorMessage =
        event.error === 'audio-capture'
          ? '마이크에 접근할 수 없습니다.'
          : event.error === 'not-allowed'
          ? '마이크 권한이 거부되었습니다.'
          : `STT 오류: ${event.error}`;
      
      console.error('[STT] 오류:', errorMessage);
      setError(errorMessage);
      if (onError) {
        onError(errorMessage);
      }
      setIsListening(false);
      recognitionStartedRef.current = false;
    };

    recognition.onend = () => {
      console.log('[STT] onend 호출됨, recognitionStarted:', recognitionStartedRef.current);
      // onend는 자동으로 호출되므로 상태만 업데이트
      recognitionStartedRef.current = false;
      
      // 의도치 않게 종료된 경우 (예: 침묵 시간 초과) 상태 동기화
      if (isListeningRef.current && !isPausedRef.current) {
        console.log('[STT] 비정상 종료 감지 (Timeout 등) -> 상태 업데이트');
        setIsListening(false);
        if (onStop) onStop();
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {
          // ignore
        }
      }
    };
  }, [onResult, onError]);

  // Convert audio blob to WAV format
  const blobToWav = useCallback(async (blob: Blob): Promise<Blob> => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }

    const audioContext = audioContextRef.current;
    const arrayBuffer = await blob.arrayBuffer();
    
    try {
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      
      const numberOfChannels = audioBuffer.numberOfChannels;
      const sampleRate = audioBuffer.sampleRate;
      const format = 1;
      const bitDepth = 16;

      const bytesPerSample = bitDepth / 8;
      const blockAlign = numberOfChannels * bytesPerSample;

      const frameLength = audioBuffer.length;
      const dataLength = frameLength * numberOfChannels * bytesPerSample;
      const buffer = new ArrayBuffer(44 + dataLength);
      const view = new DataView(buffer);

      const writeString = (offset: number, string: string) => {
        for (let i = 0; i < string.length; i++) {
          view.setUint8(offset + i, string.charCodeAt(i));
        }
      };

      writeString(0, 'RIFF');
      view.setUint32(4, 36 + dataLength, true);
      writeString(8, 'WAVE');
      writeString(12, 'fmt ');
      view.setUint32(16, 16, true);
      view.setUint16(20, format, true);
      view.setUint16(22, numberOfChannels, true);
      view.setUint32(24, sampleRate, true);
      view.setUint32(28, sampleRate * blockAlign, true);
      view.setUint16(32, blockAlign, true);
      view.setUint16(34, bitDepth, true);
      writeString(36, 'data');
      view.setUint32(40, dataLength, true);

      const channels = [];
      for (let i = 0; i < numberOfChannels; i++) {
        channels.push(audioBuffer.getChannelData(i));
      }

      let offset = 44;
      const interleaved = new Int16Array(frameLength * numberOfChannels);
      for (let i = 0; i < frameLength; i++) {
        for (let ch = 0; ch < numberOfChannels; ch++) {
          interleaved[i * numberOfChannels + ch] = Math.max(-1, Math.min(1, channels[ch][i])) < 0
            ? Math.max(-1, Math.min(1, channels[ch][i])) * 0x8000
            : Math.max(-1, Math.min(1, channels[ch][i])) * 0x7fff;
        }
      }

      for (let i = 0; i < interleaved.length; i++) {
        view.setInt16(offset, interleaved[i], true);
        offset += 2;
      }

      console.log('[Audio] WAV 변환 완료:', dataLength, '바이트');
      return new Blob([buffer], { type: 'audio/wav' });
    } catch (error) {
      console.error('[Audio] WAV 변환 실패:', error);
      throw error;
    }
  }, []);

  // Convert blob to base64
  const blobToBase64 = useCallback((blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result as string;
        const base64 = base64String.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }, []);

  const startListening = useCallback(async () => {
    console.log('[Audio] startListening 호출, isListeningRef:', isListeningRef.current);
    
    if (!recognitionRef.current || !isSupported) {
      const msg = '음성 인식을 사용할 수 없습니다.';
      setError(msg);
      if (onError) onError(msg);
      return;
    }

    if (isListeningRef.current) {
      console.log('[Audio] 이미 리스닝 중이므로 무시');
      return;
    }

    try {
      // Initialize MediaRecorder
      console.log('[Audio] 마이크 접근 시작');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        console.log('[Audio] onstop 호출됨, 총', audioChunksRef.current.length, '청크');
        mediaRecorderStartedRef.current = false;
        
        try {
          // Stop stream
          stream.getTracks().forEach((track) => track.stop());

          if (audioChunksRef.current.length === 0) {
            console.warn('[Audio] 청크가 없습니다');
            return;
          }

          // Create blob
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          console.log('[Audio] WebM Blob 크기:', audioBlob.size, '바이트');

          // 최소 1KB 이상이어야 변환 가능
          if (audioBlob.size < 1024) {
            console.warn('[Audio] 오디오 너무 작음 (< 1KB):', audioBlob.size);
            return;
          }

          // Convert to WAV
          const wavBlob = await blobToWav(audioBlob);
          console.log('[Audio] WAV Blob 크기:', wavBlob.size, '바이트');

          // Convert to base64
          const base64 = await blobToBase64(wavBlob);
          console.log('[Audio] Base64 길이:', base64.length, '문자');

          // Send audio data via WebSocket (minimum 400 chars = ~300 bytes)
          if (base64.length > 400) {
            console.log('[Audio] ✓ 오디오 데이터 전송 (충분한 크기)');
            onAudioData(base64);
          } else {
            console.warn('[Audio] ✗ 오디오 크기 부족:', base64.length, '<', 400);
          }

          audioChunksRef.current = [];
        } catch (error) {
          console.error('[Audio] onstop 처리 중 오류:', error);
        }
      };

      mediaRecorder.onerror = (event) => {
        console.error('[Audio] MediaRecorder 오류:', event);
        setError('녹음 중 오류가 발생했습니다.');
        mediaRecorderStartedRef.current = false;
      };

      mediaRecorderRef.current = mediaRecorder;
      
      // Start recording with periodic data requests
      mediaRecorder.start();
      mediaRecorderStartedRef.current = true;
      console.log('[Audio] MediaRecorder 시작');

      // Request data every 100ms
      if (dataIntervalIdRef.current) {
        clearInterval(dataIntervalIdRef.current);
      }
      dataIntervalIdRef.current = setInterval(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.requestData?.();
        }
      }, 100);

      // Start recognition
      isPausedRef.current = false;
      setIsPaused(false);
      
      if (recognitionRef.current && recognitionRef.current.start && !recognitionStartedRef.current) {
        try {
          recognitionStartedRef.current = true;
          recognitionRef.current.start();
          console.log('[Audio] 음성 인식 시작');
        } catch (err) {
          console.error('[Audio] 음성 인식 시작 오류:', err);
          recognitionStartedRef.current = false;
        }
      }

      setIsListening(true);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '마이크 접근 권한이 필요합니다.';
      console.error('[Audio] 시작 실패:', err);
      setError(msg);
      if (onError) onError(msg);
      setIsListening(false);
    }
  }, [isSupported, blobToWav, blobToBase64, onAudioData, onError]);

  const stopListening = useCallback(() => {
    console.log('[Audio] stopListening 호출됨');
    
    // 의도적인 중지이므로 ref를 먼저 업데이트하여 onend에서 비정상 종료로 감지되지 않도록 함
    isListeningRef.current = false;
    
    // Clear interval
    if (dataIntervalIdRef.current) {
      clearInterval(dataIntervalIdRef.current);
      dataIntervalIdRef.current = null;
      console.log('[Audio] 데이터 요청 인터벌 제거됨');
    }

    // Stop recognition
    if (recognitionRef.current && recognitionStartedRef.current) {
      try {
        recognitionStartedRef.current = false;
        if (recognitionRef.current.stop) {
          recognitionRef.current.stop();
        } else if (recognitionRef.current.abort) {
          recognitionRef.current.abort();
        }
        console.log('[Audio] 음성 인식 정지');
      } catch (e) {
        console.log('[Audio] 음성 인식 정지 중 오류:', e);
      }
    }

    // Stop media recorder
    if (mediaRecorderRef.current && mediaRecorderStartedRef.current) {
      try {
        if (mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop();
          mediaRecorderStartedRef.current = false;
          console.log('[Audio] MediaRecorder 정지');
        }
      } catch (e) {
        console.log('[Audio] MediaRecorder 정지 중 오류:', e);
        mediaRecorderStartedRef.current = false;
      }
    }

    // Stop stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      console.log('[Audio] 스트림 트랙 정지');
    }

    isPausedRef.current = false;
    setIsListening(false);
    setIsPaused(false);
    console.log('[Audio] 상태 초기화 완료');
  }, []);

  const pauseListening = useCallback(() => {
    console.log('[Audio] pauseListening 호출됨');
    
    if (recognitionRef.current && isListeningRef.current && !isPausedRef.current) {
      isPausedRef.current = true;
      setIsPaused(true);
      
      try {
        recognitionRef.current.abort();
        recognitionStartedRef.current = false;
        console.log('[Audio] 음성 인식 일시 중지 (abort)');
      } catch (err) {
        console.error('[Audio] 음성 인식 일시 중지 실패:', err);
      }
    }
  }, []);

  const resumeListening = useCallback(() => {
    console.log('[Audio] resumeListening 호출됨');
    
    if (!recognitionRef.current) {
      console.log('[Audio] 재개 불가: recognition 객체 없음');
      return;
    }

    if (!isListeningRef.current) {
      console.log('[Audio] 재개 불가: 음성 인식이 시작되지 않음');
      return;
    }

    if (!isPausedRef.current) {
      console.log('[Audio] 재개 불가: 이미 재개된 상태');
      return;
    }

    isPausedRef.current = false;
    setIsPaused(false);
    
    try {
      if (recognitionRef.current.start && !recognitionStartedRef.current) {
        recognitionStartedRef.current = true;
        recognitionRef.current.start();
        console.log('[Audio] 음성 인식 재개');
      }
    } catch (err) {
      console.error('[Audio] 음성 인식 재개 실패:', err);
      recognitionStartedRef.current = false;
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
