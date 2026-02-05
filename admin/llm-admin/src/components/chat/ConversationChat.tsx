'use client';

import { type ConversationMessage } from '@/types/conversation';
import { useEffect, useRef } from 'react';

interface ConversationChatProps {
  messages: ConversationMessage[];
  isLoading: boolean;
}

export default function ConversationChat({ messages, isLoading }: ConversationChatProps) {
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    // 메시지가 있을 때만 스크롤 (초기 로드 시 스크롤 방지)
    if (messages.length > 0 && chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  useEffect(() => {
    // 메시지가 추가되거나 로딩 상태가 변경될 때만 스크롤
    if (messages.length > 0) {
      scrollToBottom();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, isLoading]);

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  return (
    <div ref={chatContainerRef} className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 bg-gray-50 rounded-lg">
      {messages.length === 0 && !isLoading && (
        <div className="text-center text-gray-500 py-8">
          '모의시험 시작' 버튼을 선택하면 모의평가가 시작됩니다.
        </div>
      )}

      {messages.map((message, index) => (
        <div
          key={index}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`
              max-w-[80%] rounded-lg px-4 py-2 shadow-sm
              ${message.role === 'user'
                ? 'bg-sky-600 text-white'
                : 'bg-white text-gray-800 border border-gray-200'
              }
            `}
          >
            <div className="text-sm font-medium mb-1">
              {message.role === 'user' ? '나' : 'AI평가자'}
            </div>
            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
            <div className="text-xs opacity-70 mt-1">
              {formatTime(message.timestamp)}
            </div>
            {/* {message.evaluation && (
              <div className="mt-2 pt-2 border-t border-gray-300">
                <div className="text-xs font-semibold text-sky-600">
                  점수: {message.evaluation.score.toFixed(1)}점
                </div>
              </div>
            )} */}
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-white rounded-lg px-4 py-2 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
            </div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}

