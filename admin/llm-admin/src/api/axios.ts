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

interface FailedRequest {
  resolve: (value: unknown) => void;
  reject: (reason?: any) => void;
}

let isRefreshing = false;
let failedQueue: FailedRequest[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

// Add a response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't tried to refresh yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise(function (resolve, reject) {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { refreshToken, setAccessToken, setRefreshToken } = useAuthStore.getState().auth;

        if (!refreshToken) {
            throw new Error('No refresh token available');
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

        // Process queued requests with the new token
        processQueue(null, access_token);

        // Update the header for the original request
        originalRequest.headers.Authorization = `Bearer ${access_token}`;

        // Retry the original request
        return api(originalRequest);
      } catch (refreshError) {
        // Process queued requests with error
        processQueue(refreshError, null);
        
        // Refresh failed, logout
        useAuthStore.getState().auth.reset();
        
        // Show notification and redirect
        if (typeof window !== 'undefined') {
            toast.error('인증 정보가 만료되었습니다. 다시 로그인해주세요.');
            window.location.href = '/sign-in';
        }

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
