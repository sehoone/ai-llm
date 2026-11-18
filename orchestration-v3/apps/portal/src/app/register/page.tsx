'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { useAuthStore } from '@/stores/auth-store';

// 셀프 가입(ADR-0020): 백엔드가 role=USER로 계정 생성 후 즉시 JWT 발급.
// 전역 401 인터셉터를 피하려고 기본 axios로 직접 호출(로그인과 동일 패턴).
const REGISTER_URL = `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/auth/register`;

export default function RegisterPage() {
  const router = useRouter();
  const { auth } = useAuthStore();

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(REGISTER_URL, { username, email, password });
      const data = res.data?.data ?? res.data; // ApiResponse<T> 수동 언랩
      auth.setSession(data.access_token);
      router.replace('/');
    } catch (err) {
      const status = axios.isAxiosError(err) ? err.response?.status : undefined;
      const detail = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.response?.data?.message)
        : undefined;
      setError(status === 409 ? (detail ?? '이미 사용 중인 계정입니다.') : '가입에 실패했습니다. 입력값을 확인하세요.');
      setLoading(false);
    }
  }

  const field = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500';

  return (
    <div className="flex min-h-svh items-center justify-center p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-5 rounded-xl border border-slate-200 bg-white p-8 shadow-sm"
      >
        <div className="space-y-1 text-center">
          <h1 className="text-xl font-semibold">회원가입</h1>
          <p className="text-sm text-slate-500">새 계정을 만들어 시작하세요.</p>
        </div>

        <div className="space-y-2">
          <label htmlFor="username" className="text-sm font-medium">아이디</label>
          <input
            id="username"
            autoComplete="username"
            autoFocus
            minLength={3}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
            required
            className={field}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="email" className="text-sm font-medium">이메일</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            required
            className={field}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="password" className="text-sm font-medium">비밀번호</label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            required
            className={field}
          />
          <p className="text-xs text-slate-400">8자 이상</p>
        </div>

        <div className="space-y-2">
          <label htmlFor="confirm" className="text-sm font-medium">비밀번호 확인</label>
          <input
            id="confirm"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            disabled={loading}
            required
            className={field}
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-slate-900 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {loading ? '가입 중…' : '회원가입'}
        </button>

        <p className="text-center text-sm text-slate-500">
          이미 계정이 있으신가요?{' '}
          <a href="/login" className="font-medium text-slate-900 underline">로그인</a>
        </p>
      </form>
    </div>
  );
}
