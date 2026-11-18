'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import axios from 'axios';
import { useAuthStore } from '@/stores/auth-store';

// 백엔드가 ID/PW를 검증하고 HS256 JWT를 발급 (ADR-0009). 전역 401 인터셉터를 피하려고
// 로그인 요청은 기본 axios로 직접 호출한다. (web 로그인 흐름과 동일)
const LOGIN_URL = `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/auth/login`;

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { auth } = useAuthStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await axios.post(LOGIN_URL, { username, password });
      const data = res.data?.data ?? res.data; // ApiResponse<T> 수동 언랩
      auth.setSession(data.access_token);
      router.replace(searchParams.get('redirect') || '/');
    } catch {
      setError('아이디 또는 비밀번호가 올바르지 않습니다.');
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="w-full max-w-sm space-y-6 rounded-xl border border-slate-200 bg-white p-8 shadow-sm"
    >
      <div className="space-y-1 text-center">
        <h1 className="text-xl font-semibold">로그인</h1>
        <p className="text-sm text-slate-500">계정 정보로 로그인하세요.</p>
      </div>

      <div className="space-y-2">
        <label htmlFor="username" className="text-sm font-medium">
          아이디
        </label>
        <input
          id="username"
          autoComplete="username"
          autoFocus
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={loading}
          required
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="password" className="text-sm font-medium">
          비밀번호
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={loading}
          required
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-md bg-slate-900 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
      >
        {loading ? '로그인 중…' : '로그인'}
      </button>

      <p className="text-center text-sm text-slate-500">
        계정이 없으신가요?{' '}
        <a href="/register" className="font-medium text-slate-900 underline">
          회원가입
        </a>
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-svh items-center justify-center p-4">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
