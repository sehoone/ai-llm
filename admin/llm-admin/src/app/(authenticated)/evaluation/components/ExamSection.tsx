'use client';

import ConversationChat from '@/components/chat/ConversationChat';
import VoiceInput from '@/components/voice/VoiceInput';
import { type ConversationMessage } from '@/types/conversation';

type RecognitionControls = {
  pause: () => void;
  resume: () => void;
  stop: () => void;
};

type ExamSectionProps = {
  messages: ConversationMessage[];
  isLoading: boolean;
  isConnected: boolean;
  examCompleted: boolean;
  isExamStarted: boolean;
  isAIPlaying: boolean;
  handlePlayAudio: (audioBase64: string) => void;
  handleSpeechResult: (text: string) => void;
  handleAudioData: (audioBase64: string, format: string) => void;
  handleStartExam: () => void;
  handleEndExam: () => void;
  handleRecognitionReady: (controls: RecognitionControls) => void;
  onVoiceError?: (error: string) => void;
};

export default function ExamSection({
  messages,
  isLoading,
  isConnected,
  examCompleted,
  isExamStarted,
  isAIPlaying,
  handleSpeechResult,
  handleAudioData,
  handleStartExam,
  handleEndExam,
  handleRecognitionReady,
  onVoiceError,
}: ExamSectionProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="lg:col-span-2">
        <div className="bg-white rounded-lg shadow-lg p-6 h-[600px] flex flex-col">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">대화</h2>
          <ConversationChat messages={messages} isLoading={isLoading} />

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
                      : 'bg-gray-400 cursor-not-allowed'}
                  `}
                >
                  <div className="flex items-center gap-3">
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" />
                    </svg>
                    <span>모의시험 시작</span>
                  </div>
                </button>
                <p className="text-center text-sm text-gray-600">버튼을 클릭하면 음성 대화 모의시험이 시작됩니다</p>
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
                    onError={onVoiceError}
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
        </div>
      </div>
    </div>
  );
}

