import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

// 인증 게이트(ADR-0020): access_token 쿠키가 없으면 로그인으로. web의 (authenticated)과 동일 패턴.
// 토큰 "검증"이 아니라 존재 확인만 — 실제 검증·만료는 api가 401로 판정하고 axios가 재로그인 유도.
export default async function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  const token = (await cookies()).get('access_token')?.value;
  if (!token) redirect('/login');
  return <>{children}</>;
}
