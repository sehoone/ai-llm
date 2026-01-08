'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useWebSocket } from '@/hooks/websocket/useWebSocket';
import ExamSection from './components/ExamSection';
import EvaluationHeader from './components/EvaluationHeader';
import EvaluationSection from './components/EvaluationSection';
import PronunciationDebugPanel from '@/components/debug/PronunciationDebugPanel';
import { ConversationMessage } from '@/types/conversation';
import EvaluationResult from '@/components/evaluation/EvaluationResult';
import VoiceInput from '@/components/voice/VoiceInput';
import ConversationChat from '@/components/chat/ConversationChat';
import AIAvatar from '@/components/avatar/AIAvatar';

type ScreenMode = 'exam' | 'evaluation';

export default function EvaluationPage() {
  const { isConnected, messages, error, isLoading, sendText, reset, evaluate, evaluation, sendAudio, addLocalMessage } = useWebSocket();
  const [screenMode, setScreenMode] = useState<ScreenMode>('exam');
  const [currentEvaluation, setCurrentEvaluation] = useState<ConversationMessage | null>(null);
  const [examCompleted, setExamCompleted] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastAudioRef = useRef<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const [isAudioEnabled, setIsAudioEnabled] = useState(false);
  const [isExamStarted, setIsExamStarted] = useState(false);
  const isExamStartedRef = useRef(false);
  const recognitionControlsRef = useRef<{ pause: () => void; resume: () => void; stop: () => void } | null>(null);
  const isAudioPlayingRef = useRef(false);
  const examStartTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [isAIPlaying, setIsAIPlaying] = useState(false);
  const [currentAIText, setCurrentAIText] = useState<string | undefined>(undefined);
  const [showDebugChat, setShowDebugChat] = useState(true);

  const handleRecognitionReady = useCallback((controls: { pause: () => void; resume: () => void; stop: () => void }) => {
    recognitionControlsRef.current = controls;
    console.log('음성 인식 컨트롤 준비 완료');
  }, []);

  // 모의시험 시작 핸들러
  const handleStartExam = useCallback(() => {
    // 기존 대화 이력 초기화
    reset();
    setCurrentEvaluation(null);
    setExamCompleted(false);
    setScreenMode('exam');
    lastAudioRef.current = null;
    
    // 오디오 컨텍스트 활성화
    if (!audioContextRef.current) {
      try {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        audioContextRef.current = new AudioContextClass();
        setIsAudioEnabled(true);
        console.log('오디오 컨텍스트 활성화됨');
      } catch (err) {
        console.error('오디오 컨텍스트 생성 실패:', err);
      }
    } else if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume().then(() => {
        setIsAudioEnabled(true);
        console.log('오디오 컨텍스트 재개됨');
      });
    }
    
    // 모의시험 시작
    setIsExamStarted(true);
    isExamStartedRef.current = true;
    console.log('모의시험 시작');
    
    // AI가 먼저 질문하도록 초기 메시지 전송
    if (isConnected) {
      console.log('AI 초기 질문 요청');
      // 약간의 딜레이 후 전송하여 음성 인식이 준비될 시간 확보
      if (examStartTimeoutRef.current) clearTimeout(examStartTimeoutRef.current);
      
      examStartTimeoutRef.current = setTimeout(() => {
        sendText('모의평가 시작');
        examStartTimeoutRef.current = null;
      }, 500);
    }
  }, [isConnected, sendText, reset]);

  // 모의시험 종료 핸들러
  const handleEndExam = useCallback(() => {
    console.log('모의시험 종료');
    
    // 시작 대기 중인 타임아웃이 있다면 취소
    if (examStartTimeoutRef.current) {
      clearTimeout(examStartTimeoutRef.current);
      examStartTimeoutRef.current = null;
      console.log('AI 초기 질문 요청 취소됨');
    }
    
    // 음성 인식 완전 중지
    if (recognitionControlsRef.current) {
      try {
        // 먼저 완전히 중지
        recognitionControlsRef.current.stop();
        console.log('음성 인식 완전 중지됨');
      } catch (err) {
        console.error('음성 인식 중지 실패:', err);
        // stop이 실패하면 pause 시도
        try {
          recognitionControlsRef.current.pause();
        } catch (pauseErr) {
          console.error('음성 인식 일시 중지도 실패:', pauseErr);
        }
      }
    }
    
    // 재생 중인 오디오 정지
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
      console.log('오디오 재생 정지됨');
    }
    
    // 상태 초기화
    setIsExamStarted(false);
    isExamStartedRef.current = false;
    setIsAudioEnabled(false);
    isAudioPlayingRef.current = false;
    setIsAIPlaying(false);
    
    // 평가 완료 상태로 변경
    setExamCompleted(true);
    
    console.log('모의시험 종료 완료');
  }, []);

  // 음성 인식 오류 핸들러
  const handleVoiceError = useCallback((errorMsg: string) => {
    console.error('음성 인식 오류 발생:', errorMsg);
    alert(`음성 인식 오류: ${errorMsg}\n모의시험을 중단합니다.`);
    handleEndExam();
  }, [handleEndExam]);

  // 음성 인식 결과 처리
  const handleSpeechResult = (text: string) => {
    // 모의평가가 종료된 상태면 입력 무시
    if (!isExamStarted) {
      console.log('모의평가 종료 상태 - 사용자 입력 무시:', text);
      return;
    }
    
    // AI 음성 재생 중이면 입력 무시
    if (isAudioPlayingRef.current) {
      console.log('AI 음성 재생 중 - 사용자 입력 무시:', text);
      return;
    }
    
    if (text.trim() && isConnected && !isLoading && isExamStarted) {
      console.log('브라우저 STT 결과 (화면 표시용):', text);
      addLocalMessage(text.trim());
      // sendText(text.trim()); // 중복 전송 방지를 위해 텍스트 전송은 하지 않음 (오디오 데이터가 전송됨)
    }
  };

  const handleAudioData = (audioBase64: string, format: string) => {
    // 모의평가가 종료된 상태면 오디오 데이터 무시
    if (!isExamStartedRef.current) {
      console.log('모의평가 종료 상태 - 오디오 데이터 무시');
      return;
    }
    
    // AI 음성 재생 중이면 오디오 데이터 무시
    if (isAudioPlayingRef.current) {
      console.log('AI 음성 재생 중 - 오디오 데이터 무시');
      return;
    }

    console.log('[EvaluationPage] 오디오 데이터 수신, 길이:', audioBase64.length);
    sendAudio(audioBase64, format);
  };

  // AI 응답 오디오 자동 재생 (Azure Avatar 사용 시 텍스트 전달로 변경)
  useEffect(() => {
    console.log('메시지 업데이트됨, 총 메시지:', messages.length);
    
    const lastMessage = messages[messages.length - 1];
    
    if (lastMessage) {
      console.log('마지막 메시지:', {
        role: lastMessage.role,
        hasAudio: !!lastMessage.audio,
        audioLength: lastMessage.audio?.length,
        content: lastMessage.content.substring(0, 50)
      });
    }
    
    if (
      lastMessage &&
      lastMessage.role === 'assistant' &&
      lastMessage.content !== lastAudioRef.current
    ) {
      console.log('새로운 AI 응답 감지, 아바타 발화 시도');
      lastAudioRef.current = lastMessage.content;
      
      // AI 음성 재생 플래그 설정
      isAudioPlayingRef.current = true;
      setIsAIPlaying(true);
      
      // 아바타에게 텍스트 전달
      setCurrentAIText(lastMessage.content);
      
      console.log('AI 아바타 발화 요청 - 사용자 입력 차단');
      
      // 기존 오디오 정리
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        audioRef.current = null;
      }

            // 새 오디오 재생
      const playAudio = async () => {
        try {
          const audioUrl = `data:audio/mpeg;base64,${lastMessage.audio}`;
          console.log('오디오 URL 생성, 길이:', audioUrl.length);
          
          const audio = new Audio(audioUrl);
          
          audio.onloadeddata = () => {
            console.log('오디오 로드 완료');
          };
          
          audio.onerror = (e) => {
            console.error('오디오 로드 오류:', e);
            // 오류 발생 시 플래그 해제 및 음성 인식 재개
            isAudioPlayingRef.current = false;
            setIsAIPlaying(false);
            console.log('AI 음성 재생 종료 (오류) - 사용자 입력 허용');
          };
          
          audio.onplay = () => {
            console.log('AI 음성 재생 중... (사용자 입력 차단됨)');
          };
          
          audio.onended = () => {
            console.log('오디오 재생 완료');
            // 오디오 재생 종료 후 충분한 시간을 두고 음성 인식 재개
            setTimeout(() => {
              isAudioPlayingRef.current = false;
              setIsAIPlaying(false);
              console.log('AI 음성 재생 종료 - 사용자 입력 허용');
            }, 1500); // 1.5초 대기 후 재개
          };
          
          // 오디오 컨텍스트가 활성화되어 있는지 확인
          if (audioContextRef.current && audioContextRef.current.state === 'suspended') {
            await audioContextRef.current.resume();
          }
          
          // 자동 재생
          const playPromise = audio.play();
          
          if (playPromise !== undefined) {
            playPromise
              .then(() => {
                console.log('오디오 재생 시작됨');
              })
              .catch((err) => {
                console.error('오디오 자동 재생 실패:', err);
                console.error('에러 이름:', err.name);
                console.error('에러 메시지:', err.message);
                
                if (err.name === 'NotAllowedError') {
                  console.warn('자동 재생이 브라우저에 의해 차단되었습니다.');
                  // 사용자에게 클릭을 유도하는 알림 표시 (선택사항)
                  alert('음성 재생을 위해 화면을 한 번 클릭해주세요.');
                }
              });
          }
          
          audioRef.current = audio;
        } catch (err) {
          console.error('오디오 재생 오류:', err);
        }
      };
      
      playAudio();
    }
  }, [messages]);

  // 평가 결과 업데이트 감지
  useEffect(() => {
    if (evaluation && evaluation.evaluation) {
      setCurrentEvaluation(evaluation);
    }
  }, [evaluation]);

  // 평가결과 보기 핸들러
  const handleShowEvaluation = useCallback(() => {
    // 이전 평가 결과 초기화
    setCurrentEvaluation(null);
    // 평가 화면으로 전환
    setScreenMode('evaluation');
    // 평가 요청 전송
    evaluate();
    // 평가 결과가 오면 useEffect에서 currentEvaluation이 업데이트됨
  }, [evaluate]);

  // 모의시험 화면으로 돌아가기
  const handleBackToExam = useCallback(() => {
    setScreenMode('exam');
  }, []);

  const handlePlayAudio = (audioBase64: string) => {
    // 기존 오디오 정지
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    
    try {
      const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`);
      audio.play()
        .then(() => {
          console.log('오디오 재생 시작됨');
        })
        .catch((err) => {
          console.error('오디오 재생 실패:', err);
        });
      audioRef.current = audio;
    } catch (err) {
      console.error('오디오 재생 오류:', err);
    }
  };

  const renderControls = () => (
    <div className="mt-4 pt-4 border-t border-gray-200">
      {!isExamStarted ? (
        <div className="flex flex-col items-center justify-center gap-4">
          <button
            onClick={handleStartExam}
            disabled={!isConnected}
            className={`
              px-8 py-4 rounded-lg font-bold text-white text-lg transition-all duration-200
              shadow-lg hover:shadow-xl transform hover:scale-105
              ${isConnected
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700'
                : 'bg-gray-400 cursor-not-allowed'
              }
            `}
          >
            <div className="flex items-center gap-3">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" />
              </svg>
              <span>모의시험 시작</span>
            </div>
          </button>
          {examCompleted && (
            <p className="text-center text-sm text-green-600 font-medium mt-2">
              모의시험이 완료되었습니다. 평가 결과를 확인하세요.
            </p>
          )}
        </div>
      ) : (
        <>
          <div className="flex items-center justify-center">
            <VoiceInput
              onSpeechResult={handleSpeechResult}
              onAudioData={handleAudioData}
              disabled={!isConnected || isLoading || !isExamStarted || isAIPlaying}
              autoStart={isConnected && isExamStarted}
              onRecognitionReady={handleRecognitionReady}
              onError={handleVoiceError}
            />
          </div>
          <p className="text-center text-sm text-gray-500 mt-2">
            {isAIPlaying ? 'AI가 음성 답변 중입니다...' : '말씀하시면 자동으로 인식되어 AI가 음성으로 응답합니다'}
          </p>
          <div className="flex justify-center mt-4">
            <button
              onClick={handleEndExam}
              className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>모의평가 종료</span>
            </button>
          </div>
        </>
      )}
    </div>
  );

  return (
        <div className={`${screenMode === 'evaluation' ? 'min-h-screen overflow-y-auto' : 'h-screen overflow-hidden'} bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col`}>
          <div className={`container mx-auto px-4 pt-4 pb-20 max-w-7xl ${screenMode === 'evaluation' ? '' : 'flex-1 flex flex-col min-h-0'}`}>
            {/* 헤더 */}
            <EvaluationHeader
              screenMode={screenMode}
              isConnected={isConnected}
              examCompleted={examCompleted}
              onShowEvaluation={handleShowEvaluation}
              onBackToExam={handleBackToExam}
            />
    
            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-4">
                {error}
              </div>
            )}
    
            {screenMode === 'exam' ? (
              /* 모의시험 화면 */
              <div className={showDebugChat ? "grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0" : "flex flex-col items-center gap-6 flex-1 min-h-0"}>
                {/* 왼쪽: AI 아바타 영역 */}
                <div className={showDebugChat ? "lg:col-span-1 h-full" : "w-full flex-1 min-h-0"}>
                  {isExamStarted ? (
                    // <AIAvatar 
                    //   isTalking={isAIPlaying} 
                    //   textToSpeak={currentAIText}
                    //   onSpeechStart={() => {
                    //       console.log("Avatar started speaking");
                    //       setIsAIPlaying(true);
                    //       isAudioPlayingRef.current = true;
                    //       if (recognitionControlsRef.current) recognitionControlsRef.current.pause();
                    //   }}
                    //   onSpeechEnd={() => {
                    //       console.log("Avatar finished speaking");
                    //       setIsAIPlaying(false);
                    //       isAudioPlayingRef.current = false;
                          
                    //       if (recognitionControlsRef.current) {
                    //           setTimeout(() => recognitionControlsRef.current?.resume(), 1000);
                    //       }
                    //   }}
                    // />
                    <div>disable avatar</div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gray-100 rounded-lg shadow-lg border border-gray-200">
                      <div className="text-center p-6">
                        <div className="w-20 h-20 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
                          <svg className="w-10 h-10 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-800 mb-2">AI 면접관 대기 중</h3>
                        <p className="text-gray-600">모의평가를 시작하면 면접관이 나옵니다.</p>
                      </div>
                    </div>
                  )}
                </div>
    
                {/* 오른쪽: 대화 영역 */}
                {showDebugChat ? (
                    <div className="lg:col-span-2 h-full min-h-0">
                      <div className="bg-white rounded-lg shadow-lg p-6 h-full flex flex-col relative min-h-0">
                        <h2 className="text-xl font-semibold text-gray-800 mb-4 flex-shrink-0">대화내용(디버깅용)</h2>
                        
                        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
                          <ConversationChat 
                            messages={messages} 
                            isLoading={isLoading}
                          />
                        </div>
        
                        {/* 음성 입력 영역 */}
                        <div className="flex-shrink-0">
                          {renderControls()}
                        </div>
                      </div>
                    </div>
                ) : (
                    <div className="w-full max-w-lg">
                        {renderControls()}
                    </div>
                )}
    
              </div>
            ) : (
              /* 평가결과 화면 */
              <EvaluationSection isLoading={isLoading} currentEvaluation={currentEvaluation} />
            )}
          </div>

      <PronunciationDebugPanel 
        showDebugChat={showDebugChat}
        onToggleDebugChat={() => setShowDebugChat(!showDebugChat)}
      />
    </div>
  );
}

