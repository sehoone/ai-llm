'use client';

import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';

// 랜딩(최소 골격): 로그인 사용자 확인 + 로그아웃. 실제 사용자 기능(chat 등)은 후속 회차 이식.
export default function HomePage() {
  const router = useRouter();
  const { auth } = useAuthStore();

  function logout() {
    auth.reset();
    router.replace('/login');
  }

  const name = auth.user?.username || auth.user?.email || auth.user?.sub || '사용자';

  return (
    <main className="mx-auto flex min-h-svh max-w-2xl flex-col items-center justify-center gap-6 p-6 text-center">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">AI 포털</h1>
        <p className="text-slate-500">
          <span className="font-medium text-slate-900">{name}</span>님, 환영합니다.
        </p>
      </div>

      <p className="max-w-md text-sm text-slate-500">
        사용자 전용 포털입니다(ADR-0020). 관리자 화면은{' '}
        <code className="rounded bg-slate-100 px-1">/admin</code> 입니다.
      </p>

      <div className="flex items-center gap-3">
        <a
          href="/chat"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          대화 시작하기
        </a>
        <button
          onClick={logout}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-100"
        >
          로그아웃
        </button>
      </div>
    </main>
  );
}
