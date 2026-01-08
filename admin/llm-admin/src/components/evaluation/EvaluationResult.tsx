'use client';

import { Evaluation } from '@/types/conversation';
import { JSX } from 'react';

interface EvaluationResultProps {
  evaluation: Evaluation;
  className?: string;
}

export default function EvaluationResult({ evaluation, className = '' }: EvaluationResultProps) {
  const { score, feedback, suggestions, evaluation_details } = evaluation;

  // 0-100 점수를 0-10 스케일로 변환
  const toTenScale = (score: number) => (score / 10).toFixed(1);
  
  // Comprehension 점수 (communication_score를 comprehension으로 사용하거나 별도 점수)
  const comprehensionScore = evaluation_details.comprehension_score 
    ? evaluation_details.comprehension_score 
    : evaluation_details.communication_score;

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600';
    if (score >= 6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 8) return 'bg-green-100';
    if (score >= 6) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  // Expected level 계산 (0-10 스케일)
  const expectedLevel = (score / 10).toFixed(1);
  const levelText = score >= 80 ? 'IH' : score >= 70 ? 'IM' : score >= 60 ? 'IL' : 'NL';

  // 에러 타입 데이터 (파이 차트용)
  const errorTypes = evaluation_details.error_types || {};
  const errorEntries = Object.entries(errorTypes).filter(([, value]) => {
    // 숫자로 변환 가능한 값만 필터링
    const numValue = typeof value === 'number' ? value : parseFloat(String(value));
    return !isNaN(numValue) && numValue > 0;
  });
  const totalErrors = errorEntries.reduce((sum, [, value]) => {
    const numValue = typeof value === 'number' ? value : parseFloat(String(value));
    return sum + (isNaN(numValue) ? 0 : numValue);
  }, 0);
  
  // 디버깅용 로그
  console.log('에러 타입 데이터:', { errorTypes, errorEntries, totalErrors });

  // 파이 차트 색상
  const pieColors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6'];

  // 파이 차트 섹션 생성 함수
  const createPieSections = () => {
    console.log('파이 차트 생성 시작:', { errorEntries, totalErrors });
    
    if (errorEntries.length === 0 || totalErrors === 0) {
      console.log('파이 차트 데이터 없음');
      return [];
    }
    
    const sections: JSX.Element[] = [];
    let currentAngle = -90; // -90도에서 시작 (12시 방향)
    const centerX = 100;
    const centerY = 100;
    const radius = 80;
    
    // 각 항목의 각도를 미리 계산 (0이 아닌 것만)
    const validAngles = errorEntries
      .map(([errorType, count]) => {
        const value = typeof count === 'number' ? count : parseFloat(String(count));
        if (isNaN(value) || value === 0) return null;
        const percentage = (value / totalErrors) * 100;
        return { errorType, angle: (percentage / 100) * 360 };
      })
      .filter((item): item is { errorType: string; angle: number } => item !== null);
    
    if (validAngles.length === 0) return [];
    
    // 총 각도 계산
    const totalAngle = validAngles.reduce((sum, item) => sum + item.angle, 0);
    // 각도 보정 (360도가 되도록)
    const angleCorrection = totalAngle > 0 ? 360 / totalAngle : 1;

    validAngles.forEach(({ errorType, angle: originalAngle }, index) => {
      // 마지막 섹션인지 확인
      const isLast = index === validAngles.length - 1;
      
      // 보정된 각도
      let angle = originalAngle * angleCorrection;
      
      // 마지막 섹션이면 정확히 360도가 되도록 조정
      if (isLast) {
        const remainingAngle = 360 - (currentAngle + 90);
        if (Math.abs(remainingAngle) > 0.1) {
          angle = remainingAngle;
        }
      }
      
      const startAngle = currentAngle;
      const endAngle = currentAngle + angle;
      
      // 라디안 변환
      const startAngleRad = (startAngle * Math.PI) / 180;
      const endAngleRad = (endAngle * Math.PI) / 180;
      
      // 시작점과 끝점 계산
      const x1 = centerX + radius * Math.cos(startAngleRad);
      const y1 = centerY + radius * Math.sin(startAngleRad);
      const x2 = centerX + radius * Math.cos(endAngleRad);
      const y2 = centerY + radius * Math.sin(endAngleRad);
      
      // 큰 호인지 작은 호인지 판단
      const largeArcFlag = angle > 180 ? 1 : 0;
      
      // SVG path 생성
      const pathData = [
        `M ${centerX} ${centerY}`,           // 중심으로 이동
        `L ${x1} ${y1}`,                     // 시작점으로 선 그리기
        `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`, // 원호 그리기
        `Z`                                   // 중심으로 닫기
      ].join(' ');
      
      console.log(`파이 섹션 ${index}:`, { 
        errorType, 
        originalAngle: originalAngle.toFixed(2),
        angle: angle.toFixed(2),
        startAngle: startAngle.toFixed(2),
        endAngle: endAngle.toFixed(2),
        isLast
      });
      
      sections.push(
        <path
          key={`pie-section-${index}-${errorType}`}
          d={pathData}
          fill={pieColors[index % pieColors.length]}
          opacity={0.85}
          stroke="#ffffff"
          strokeWidth="2"
        />
      );
      
      currentAngle = endAngle;
    });
    
    console.log('파이 차트 섹션 생성 완료:', sections.length, '총 각도:', currentAngle + 90);
    return sections;
  };

  return (
    <div className={`bg-white rounded-lg shadow-lg p-8 ${className}`}>
      <h2 className="text-3xl font-bold mb-6 text-gray-800">Diagnostic Report</h2>

      {/* Overall Analysis */}
      <div className="mb-8">
        <h3 className="text-xl font-semibold mb-4 text-gray-700">Overall Analysis</h3>
        <div className="bg-gray-50 rounded-lg p-6">
          <div className="mb-4">
            <span className="text-lg font-semibold text-gray-700">Expected level: </span>
            <span className="text-2xl font-bold text-blue-600">{expectedLevel}/10</span>
            <span className="text-lg font-semibold text-gray-600 ml-2">{levelText}</span>
          </div>

          {/* Skill Breakdown - Bar Chart */}
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-700">Comprehension</span>
                <span className="text-sm font-bold text-gray-800">
                  {toTenScale(comprehensionScore)}/10
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div
                  className={`h-4 rounded-full transition-all duration-500 ${getScoreBgColor(comprehensionScore)}`}
                  style={{ width: `${comprehensionScore}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-700">Fluency</span>
                <span className="text-sm font-bold text-gray-800">
                  {toTenScale(evaluation_details.fluency_score)}/10
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div
                  className={`h-4 rounded-full transition-all duration-500 ${getScoreBgColor(evaluation_details.fluency_score)}`}
                  style={{ width: `${evaluation_details.fluency_score}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-700">Grammar</span>
                <span className="text-sm font-bold text-gray-800">
                  {toTenScale(evaluation_details.grammar_score)}/10
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div
                  className={`h-4 rounded-full transition-all duration-500 ${getScoreBgColor(evaluation_details.grammar_score)}`}
                  style={{ width: `${evaluation_details.grammar_score}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-700">Vocabulary</span>
                <span className="text-sm font-bold text-gray-800">
                  {toTenScale(evaluation_details.vocabulary_score)}/10
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div
                  className={`h-4 rounded-full transition-all duration-500 ${getScoreBgColor(evaluation_details.vocabulary_score)}`}
                  style={{ width: `${evaluation_details.vocabulary_score}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Overall Comment */}
      <div className="mb-8">
        <h3 className="text-xl font-semibold mb-4 text-gray-700">Overall Comment</h3>
        <div className="bg-blue-50 rounded-lg p-6">
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{feedback}</p>
        </div>
      </div>

      {/* Strength */}
      {evaluation_details.strengths && evaluation_details.strengths.length > 0 && (
        <div className="mb-8">
          <h3 className="text-xl font-semibold mb-4 text-green-700">Strength</h3>
          <ul className="space-y-3">
            {evaluation_details.strengths.map((strength, index) => (
              <li key={index} className="flex items-start gap-3 text-gray-700">
                <span className="text-green-500 mt-1 text-xl">•</span>
                <span className="flex-1">{strength}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Weakness */}
      {evaluation_details.weaknesses && evaluation_details.weaknesses.length > 0 && (
        <div className="mb-8">
          <h3 className="text-xl font-semibold mb-4 text-orange-700">Weakness</h3>
          <ul className="space-y-3">
            {evaluation_details.weaknesses.map((weakness, index) => (
              <li key={index} className="flex items-start gap-3 text-gray-700">
                <span className="text-orange-500 mt-1 text-xl">•</span>
                <span className="flex-1">{weakness}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Detailed Feedback */}
      <div className="mb-8">
        <h3 className="text-xl font-semibold mb-4 text-gray-700">Detailed Feedback</h3>
        
        {/* Most frequent error types - Pie Chart */}
        {errorEntries.length > 0 && (
          <div className="mb-6">
            <h4 className="text-lg font-medium mb-4 text-gray-700">Most frequent error types</h4>
            <div className="flex flex-wrap gap-4 mb-4">
              {errorEntries.map(([errorType, count], index) => {
                const numValue = typeof count === 'number' ? count : parseFloat(String(count));
                const percentage = totalErrors > 0 && !isNaN(numValue) 
                  ? Math.round((numValue / totalErrors) * 100) 
                  : 0;
                return (
                  <div key={index} className="flex items-center gap-2">
                    <div
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: pieColors[index % pieColors.length] }}
                    ></div>
                    <span className="text-sm text-gray-700">
                      {errorType}: {percentage}%
                    </span>
                  </div>
                );
              })}
            </div>
            {/* 간단한 파이 차트 시각화 */}
            {errorEntries.length > 0 && totalErrors > 0 ? (
              <div className="flex items-center justify-center my-6 bg-gray-50 rounded-lg p-4">
                <div className="relative" style={{ width: '200px', height: '200px', minHeight: '200px' }}>
                  <svg 
                    width="200" 
                    height="200" 
                    viewBox="0 0 200 200"
                    style={{ display: 'block' }}
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    {/* 배경 원 (디버깅용) */}
                    <circle cx="100" cy="100" r="80" fill="#f3f4f6" stroke="#e5e7eb" strokeWidth="2" />
                    {createPieSections()}
                  </svg>
                </div>
              </div>
            ) : (
              <div className="text-center text-gray-400 text-sm my-4 p-4 bg-gray-50 rounded-lg">
                에러 타입 데이터가 없습니다. (error_types: {JSON.stringify(errorTypes)})
              </div>
            )}
          </div>
        )}

        {/* Specific Corrections/Examples */}
        {evaluation_details.corrections && evaluation_details.corrections.length > 0 && (
          <div className="mb-6">
            <h4 className="text-lg font-medium mb-4 text-gray-700">Specific Corrections/Examples</h4>
            <ul className="space-y-3">
              {evaluation_details.corrections.map((correction, index) => (
                <li key={index} className="flex items-start gap-3 text-gray-700">
                  <span className="text-blue-500 mt-1 text-xl">•</span>
                  <span className="flex-1">{correction}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Category Feedback */}
        {evaluation_details.category_feedback && (
          <div className="space-y-6">
            {evaluation_details.category_feedback.comprehension && (
              <div>
                <h4 className="text-lg font-semibold mb-3 text-gray-700">Comprehension</h4>
                <ul className="space-y-2">
                  {evaluation_details.category_feedback.comprehension.map((item, index) => (
                    <li key={index} className="flex items-start gap-3 text-gray-700">
                      <span className="text-gray-400 mt-1">•</span>
                      <span className="flex-1">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {evaluation_details.category_feedback.fluency && (
              <div>
                <h4 className="text-lg font-semibold mb-3 text-gray-700">Fluency</h4>
                <ul className="space-y-2">
                  {evaluation_details.category_feedback.fluency.map((item, index) => (
                    <li key={index} className="flex items-start gap-3 text-gray-700">
                      <span className="text-gray-400 mt-1">•</span>
                      <span className="flex-1">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {evaluation_details.category_feedback.grammar && (
              <div>
                <h4 className="text-lg font-semibold mb-3 text-gray-700">Grammar</h4>
                <ul className="space-y-2">
                  {evaluation_details.category_feedback.grammar.map((item, index) => (
                    <li key={index} className="flex items-start gap-3 text-gray-700">
                      <span className="text-gray-400 mt-1">•</span>
                      <span className="flex-1">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {evaluation_details.category_feedback.vocabulary && (
              <div>
                <h4 className="text-lg font-semibold mb-3 text-gray-700">Vocabulary</h4>
                <ul className="space-y-2">
                  {evaluation_details.category_feedback.vocabulary.map((item, index) => (
                    <li key={index} className="flex items-start gap-3 text-gray-700">
                      <span className="text-gray-400 mt-1">•</span>
                      <span className="flex-1">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Suggestions */}
      {suggestions && suggestions.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold mb-4 text-blue-700">Suggestions</h3>
          <ul className="space-y-3">
            {suggestions.map((suggestion, index) => (
              <li key={index} className="flex items-start gap-3 text-gray-700">
                <span className="text-blue-500 mt-1 text-xl">•</span>
                <span className="flex-1">{suggestion}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
