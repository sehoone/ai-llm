'use client';

import EvaluationResult from '@/components/evaluation/EvaluationResult';
import { type ConversationMessage } from '@/types/conversation';

type EvaluationSectionProps = {
  isLoading: boolean;
  currentEvaluation: ConversationMessage | null;
};

export default function EvaluationSection({ isLoading, currentEvaluation }: EvaluationSectionProps) {
  return (
    <div className="max-w-4xl mx-auto">
      {isLoading ? (
        <div className="bg-white rounded-lg shadow-lg p-6 h-[600px] flex items-center justify-center">
          <div className="text-center">
            <div className="flex justify-center mb-4">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-blue-200 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-blue-600 rounded-full border-t-transparent animate-spin"></div>
              </div>
            </div>
            <p className="text-xl font-semibold text-gray-700 mb-2">평가 결과 생성 중...</p>
            <p className="text-sm text-gray-500">대화 내용을 분석하고 있습니다. 잠시만 기다려주세요.</p>
          </div>
        </div>
      ) : currentEvaluation && currentEvaluation.evaluation ? (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <EvaluationResult evaluation={currentEvaluation.evaluation} />
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-lg p-6 h-[600px] flex items-center justify-center">
          <div className="text-center text-gray-500">
            <svg
              className="w-16 h-16 mx-auto mb-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <p className="text-lg font-medium">평가 결과가 없습니다</p>
            <p className="text-sm mt-2">모의시험을 완료한 후 결과를 확인할 수 있습니다</p>
          </div>
        </div>
      )}
    </div>
  );
}

