import axios from 'axios';
import { useAuthStore } from '@/stores/auth-store';
import { toast } from 'sonner';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api', // Default to /api if not set
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the auth token if available
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().auth.accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't tried to refresh yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const { refreshToken, setAccessToken, setRefreshToken, reset } = useAuthStore.getState().auth;

        if (!refreshToken) {
          return Promise.reject(error);
        }

        // Call refresh endpoint
        const response = await axios.post(
          (process.env.NEXT_PUBLIC_API_URL || '') + '/api/v1/auth/refresh',
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token } = response.data;

        setAccessToken(access_token);
        if (refresh_token) {
          setRefreshToken(refresh_token);
        }

        // Update the header for the original request
        originalRequest.headers.Authorization = `Bearer ${access_token}`;

        // Retry the original request
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout
        useAuthStore.getState().auth.reset();
        
        // Show notification and redirect
        toast.error('인증 정보가 만료되었습니다. 다시 로그인해주세요.');
        
        if (typeof window !== 'undefined') {
          window.location.href = '/sign-in';
        }

        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
