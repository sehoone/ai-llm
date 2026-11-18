import api from './axios';

// 내 프로필·비밀번호 (ADR-0009). 자기 자신만 수정.
export interface Me {
  id: number;
  username: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

export const userApi = {
  me: async (): Promise<Me> => (await api.get<Me>('v1/users/me')).data,
  updateMe: async (body: { username?: string; email?: string }): Promise<Me> =>
    (await api.patch<Me>('v1/users/me', body)).data,
  changePassword: async (current_password: string, new_password: string): Promise<void> => {
    await api.post('v1/auth/password', { current_password, new_password });
  },
};
