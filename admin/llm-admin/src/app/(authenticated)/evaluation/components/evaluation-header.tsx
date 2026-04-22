'use client';

type ScreenMode = 'exam' | 'evaluation';

type EvaluationHeaderProps = {
  screenMode: ScreenMode;
  isConnected: boolean;
  examCompleted: boolean;
  onShowEvaluation: () => void;
  onBackToExam: () => void;
};

export default function EvaluationHeader({
  screenMode,
  isConnected,
  examCompleted,
  onShowEvaluation,
  onBackToExam,
}: EvaluationHeaderProps) {
  return (
    <div className="text-center mb-8">
      <h1 className="text-4xl font-bold text-gray-800 mb-2">음성 AI 모의평가</h1>
      <div className="mt-4 flex items-center justify-center gap-4">
        <div className={`flex items-center gap-2 ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
          <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-sm font-medium">{isConnected ? '연결됨' : '연결 안 됨'}</span>
        </div>
        {screenMode === 'exam' && examCompleted && (
          <button
            onClick={onShowEvaluation}
            className="px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition-colors text-sm font-medium"
          >
            평가 결과 보기
          </button>
        )}
        {screenMode === 'evaluation' && (
          <button
            onClick={onBackToExam}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm font-medium"
          >
            모의시험으로 돌아가기
          </button>
        )}
      </div>
    </div>
  );
}

