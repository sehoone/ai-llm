import api from './axios';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginUser {
  id: number;
  username: string;
  email: string;
  role: string;
  status: string;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  user: LoginUser;
}

export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  const response = await api.post<LoginResponse>('v1/auth/login', data);
  return response.data;
};

export const refreshToken = async (token: string): Promise<LoginResponse> => {
  const response = await api.post<LoginResponse>('v1/auth/refresh', { refreshToken: token });
  return response.data;
};

export const logout = async (token: string): Promise<void> => {
  await api.post('v1/auth/logout', { refreshToken: token });
};
