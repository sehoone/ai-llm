import axios from 'axios';
import { useAuthStore } from '@/stores/auth-store';
import { toast } from 'sonner';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api', // Default to /api if not set
  headers: {
    'Content-Type': 'application/json',
  },
});

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

function isTokenExpired() {
  const expiresAt = useAuthStore.getState().auth.expiresAt;
  if (!expiresAt) return false; // If no expiration time is set, assume it's valid or rely on 401
  
  // Convert ISO string to timestamp
  const expirationTime = new Date(expiresAt).getTime();
  // 2s buffer
  return Date.now() >= expirationTime - 2000;
}

const refreshAccessToken = async () => {
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      failedQueue.push({ resolve, reject });
    });
  }

  isRefreshing = true;

  try {
    const { refreshToken, setAccessToken, setRefreshToken, setExpiresAt } =
      useAuthStore.getState().auth;

    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    // Call refresh endpoint
    const response = await axios.post(
      (process.env.NEXT_PUBLIC_API_URL || '') + '/api/v1/auth/refresh',
      { refresh_token: refreshToken }
    );

    const { access_token, refresh_token, expires_at } = response.data;

    setAccessToken(access_token);
    if (refresh_token) {
      setRefreshToken(refresh_token);
    }
    if (expires_at) {
        setExpiresAt(expires_at);
    }

    // Process queued requests with the new token
    processQueue(null, access_token);

    return access_token;
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

    throw refreshError;
  } finally {
    isRefreshing = false;
  }
};

// Add a request interceptor to include the auth token if available
api.interceptors.request.use(
  async (config) => {
    let token = useAuthStore.getState().auth.accessToken;

    if (token && isTokenExpired()) {
      try {
        token = (await refreshAccessToken()) as string;
      } catch (error) {
        return Promise.reject(error);
      }
    }

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
        const token = await refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      } catch (err) {
        return Promise.reject(err);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
