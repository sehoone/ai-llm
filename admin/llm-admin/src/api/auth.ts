import api from './axios';
export interface LoginRequest {
  email: string;
  password: string;
  grant_type: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: string;
}

export const login = async (data: Omit<LoginRequest, 'grant_type'>): Promise<LoginResponse> => {
  const response = await api.post<LoginResponse>('/api/v1/auth/login', {
    ...data,
    grant_type: 'password',
  });
  return response.data;
};
