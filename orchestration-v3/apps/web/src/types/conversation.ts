export interface PronunciationResult {
  pronunciation_score: number;
  accuracy_score: number;
  fluency_score: number;
  prosody_score: number;
  completeness_score: number;
  recognized_text: string;
  reference_text?: string;
  word_details?: Array<{
    Word?: string;
    word?: string;
    PronunciationAssessment?: {
      PronunciationScore?: number;
      AccuracyScore?: number;
    };
    accuracy_score?: number;
    pronunciation_score?: number;
  }>;
}

export interface EvaluationDetails {
  grammar_score: number;
  vocabulary_score: number;
  fluency_score: number;
  communication_score: number;
  comprehension_score?: number;
  strengths: string[];
  weaknesses: string[];
  error_types?: Record<string, number>;
  corrections?: string[];
  category_feedback?: {
    comprehension?: string[];
    fluency?: string[];
    grammar?: string[];
    vocabulary?: string[];
  };
}

export interface Evaluation {
  score: number;
  feedback: string;
  suggestions: string[];
  evaluation_details: EvaluationDetails;
}

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  evaluation?: Evaluation;
  audio?: string;
  pronunciation?: PronunciationResult;
  isLocal?: boolean; // 로컬에서 추가된 메시지인지 여부
}

export interface ConversationResponse {
  type?: 'user_text' | 'assistant_text' | 'evaluation' | 'error';
  text?: string;
  audio?: string;
  pronunciation?: PronunciationResult;
  evaluation?: Evaluation;
  error?: string;
}

