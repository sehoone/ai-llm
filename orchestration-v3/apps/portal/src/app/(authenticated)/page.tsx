import { redirect } from 'next/navigation';

// 로그인 후 진입점은 바로 채팅(claude.ai 패턴). 별도 랜딩 없이 /chat으로.
export default function HomePage() {
  redirect('/chat');
}
