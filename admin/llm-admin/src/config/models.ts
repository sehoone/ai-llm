export const LLM_MODELS = [
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
  },
  {
    id: 'gpt-5',
    name: 'GPT-5',
  },
  {
    id: 'gpt-5-mini',
    name: 'GPT-5 Mini',
  },
  {
    id: 'o1-mini',
    name: 'o1 Mini',
  },
  
] as const;

export type LlmModel = typeof LLM_MODELS[number]['id'];

export const DEFAULT_LLM_MODEL: LlmModel = 'gpt-4o-mini';
