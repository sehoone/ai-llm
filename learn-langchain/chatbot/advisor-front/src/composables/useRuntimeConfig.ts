import { reactive } from 'vue';

const runtimeConfig = reactive({
  public: {
    appName: 'chatbot' // Replace with your actual app name or other public config
  },
  private: {
    apiBaseUrl: 'http://localhost:5100' // Replace with your actual API base URL or other private config
  }
});

export function useRuntimeConfig() {
  return runtimeConfig;
}
