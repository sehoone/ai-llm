import type { Metadata } from 'next';

// eslint-disable-next-line react-refresh/only-export-components
export const metadata: Metadata = {
  title: '음성 AI 평가',
  description: '음성 기반 음성 모의평가와 평가 결과 확인 화면입니다.',
};

export default function EvaluationLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

