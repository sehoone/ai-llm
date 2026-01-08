'use client';

import { useRef, useEffect, useState, createContext, useContext } from 'react';

interface PronunciationLog {
  timestamp: Date;
  phase: 'stt' | 'assessment';
  text: string;
}

interface AssessmentResult {
  recognized_text: string;
  reference_text: string;
  accuracy_score: number;
  pronunciation_score: number;
  completeness_score: number;
  fluency_score: number;
  prosody_score: number;
  word_details?: Array<{
    word: string;
    accuracy_score: number;
    pronunciation_score: number;
  }>;
}

// Global context for sharing debug data
const DebugContext = createContext<{
  assessmentData: AssessmentResult | null;
  setAssessmentData: (data: AssessmentResult | null) => void;
} | null>(null);

export function useDebugContext() {
  return useContext(DebugContext);
}

// Global state to store assessment data
let globalAssessmentData: AssessmentResult | null = null;
let globalDebugCallbacks: Array<(data: AssessmentResult) => void> = [];

export function registerDebugCallback(callback: (data: AssessmentResult) => void) {
  globalDebugCallbacks.push(callback);
}

export function setGlobalAssessmentData(data: AssessmentResult) {
  globalAssessmentData = data;
  globalDebugCallbacks.forEach(cb => cb(data));
}

interface PronunciationDebugPanelProps {
  showDebugChat?: boolean;
  onToggleDebugChat?: () => void;
}

export default function PronunciationDebugPanel({ showDebugChat, onToggleDebugChat }: PronunciationDebugPanelProps) {
  const [logs, setLogs] = useState<PronunciationLog[]>([]);
  const [assessmentResult, setAssessmentResult] = useState<AssessmentResult | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Listen for global assessment data updates
  useEffect(() => {
    const callback = (data: AssessmentResult) => {
      console.log('[PronunciationDebugPanel] 평가 데이터 업데이트:', data);
      setAssessmentResult(data);
      setLogs(prev => [...prev, {
        timestamp: new Date(),
        phase: 'assessment',
        text: `[발음 평가] 평가 완료 - 정확도: ${data.accuracy_score.toFixed(1)}, 발음: ${data.pronunciation_score.toFixed(1)}`
      }]);
    };
    
    registerDebugCallback(callback);
    
    // If data already exists, display it
    if (globalAssessmentData) {
      console.log('[PronunciationDebugPanel] 기존 평가 데이터 발견:', globalAssessmentData);
      setAssessmentResult(globalAssessmentData);
    }
    
    return () => {
      globalDebugCallbacks = globalDebugCallbacks.filter(cb => cb !== callback);
    };
  }, []);

  // Override console.log to capture logs
  useEffect(() => {
    const originalLog = console.log;

    const consoleLogHandler = (...args: any[]) => {
      originalLog(...args);

      const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
      ).join(' ');

      // Parse STT and assessment logs
      if (message.includes('[STT]') || message.includes('[발음 평가]') || message.includes('[Azure STT]') || message.includes('[Whisper STT]')) {
        setLogs(prev => [...prev, {
          timestamp: new Date(),
          phase: message.includes('[발음 평가]') ? 'assessment' : 'stt',
          text: message
        }]);
      }
    };

    console.log = consoleLogHandler;

    return () => {
      console.log = originalLog;
    };
  }, []);

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 85) return 'bg-green-50';
    if (score >= 70) return 'bg-yellow-50';
    return 'bg-red-50';
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gray-900 text-gray-100 border-t border-gray-700 shadow-2xl">
      {/* Header */}
      <div 
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-800 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <svg 
            className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="currentColor" 
            viewBox="0 0 20 20"
          >
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
          <span className="font-semibold text-sm">발음 평가 디버그 패널</span>
          {assessmentResult && (
            <span className="ml-3 text-xs bg-blue-600 px-2 py-1 rounded">
              점수: {assessmentResult.accuracy_score.toFixed(1)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onToggleDebugChat && (
            <button 
              onClick={(e) => {
                e.stopPropagation();
                onToggleDebugChat();
              }}
              className="text-xs px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
            >
              {showDebugChat ? '채팅 숨기기' : '채팅 보이기'}
            </button>
          )}
          <button 
            onClick={(e) => {
              e.stopPropagation();
              setLogs([]);
              setAssessmentResult(null);
            }}
            className="text-xs px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
          >
            초기화
          </button>
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="max-h-96 overflow-y-auto border-t border-gray-700 grid grid-cols-2 gap-4 p-4">
          {/* Left: Logs */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-gray-300 mb-2">실시간 로그</h3>
            <div className="bg-gray-950 rounded p-3 h-64 overflow-y-auto font-mono text-xs space-y-1 border border-gray-700">
              {logs.length === 0 ? (
                <p className="text-gray-500">음성 입력을 대기 중...</p>
              ) : (
                <>
                  {logs.map((log, idx) => (
                    <div 
                      key={idx} 
                      className={`${
                        log.phase === 'assessment' ? 'text-blue-300' : 'text-green-300'
                      } text-xs leading-relaxed`}
                    >
                      <span className="text-gray-500">[{log.timestamp.toLocaleTimeString()}]</span> {log.text}
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {logs.length} 로그 항목
            </p>
          </div>

          {/* Right: Assessment Results */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-gray-300 mb-2">평가 결과</h3>
            {assessmentResult ? (
              <div className="bg-gray-950 rounded p-3 border border-gray-700 space-y-3">
                {/* Texts */}
                <div className="space-y-2">
                  <div className="text-xs">
                    <p className="text-gray-400">인식 텍스트:</p>
                    <p className="text-gray-200 mt-1">"{assessmentResult.recognized_text}"</p>
                  </div>
                  <div className="text-xs">
                    <p className="text-gray-400">참조 텍스트:</p>
                    <p className="text-gray-200 mt-1">"{assessmentResult.reference_text}"</p>
                  </div>
                </div>

                {/* Scores */}
                <div className="space-y-1 text-xs">
                  <p className="text-gray-400 font-semibold mb-2">점수</p>
                  <div className={`p-2 rounded ${assessmentResult.accuracy_score}`}>
                    <div className="flex justify-between items-center">
                      <span>정확도</span>
                      <span className={`font-bold ${getScoreColor(assessmentResult.accuracy_score)}`}>
                        {assessmentResult.accuracy_score.toFixed(1)}
                      </span>
                    </div>
                  </div>
                  <div className={`p-2 rounded ${assessmentResult.pronunciation_score}`}>
                    <div className="flex justify-between items-center">
                      <span>발음</span>
                      <span className={`font-bold ${getScoreColor(assessmentResult.pronunciation_score)}`}>
                        {assessmentResult.pronunciation_score.toFixed(1)}
                      </span>
                    </div>
                  </div>
                  <div className={`p-2 rounded ${assessmentResult.completeness_score}`}>
                    <div className="flex justify-between items-center">
                      <span>완성도</span>
                      <span className={`font-bold ${getScoreColor(assessmentResult.completeness_score)}`}>
                        {assessmentResult.completeness_score.toFixed(1)}
                      </span>
                    </div>
                  </div>
                  <div className={`p-2 rounded ${assessmentResult.fluency_score}`}>
                    <div className="flex justify-between items-center">
                      <span>유창성</span>
                      <span className={`font-bold ${getScoreColor(assessmentResult.fluency_score)}`}>
                        {assessmentResult.fluency_score.toFixed(1)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Word Details */}
                {assessmentResult.word_details && assessmentResult.word_details.length > 0 && (
                  <div className="space-y-1 text-xs border-t border-gray-700 pt-2">
                    <p className="text-gray-400 font-semibold mb-1">단어별 분석</p>
                    <div className="space-y-1 max-h-20 overflow-y-auto">
                      {assessmentResult.word_details.map((word, idx) => (
                        <div key={idx} className="bg-gray-800 p-1.5 rounded text-xs">
                          <div className="flex justify-between items-center">
                            <span className="font-mono">{word.word}</span>
                            <span className="text-gray-400 text-xs">
                              {word.accuracy_score.toFixed(1)}/{word.pronunciation_score.toFixed(1)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-gray-950 rounded p-4 border border-gray-700 h-64 flex items-center justify-center text-center">
                <p className="text-sm text-gray-500">
                  음성을 인식하면 평가 결과가<br />여기에 표시됩니다
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
