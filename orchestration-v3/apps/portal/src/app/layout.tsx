import '@/styles/index.css';
import type { Metadata } from 'next';
import { Noto_Sans_KR } from 'next/font/google';
import { Providers } from './providers';

const notoSansKR = Noto_Sans_KR({
  subsets: ['latin'],
  weight: ['300', '400', '500', '700'],
  variable: '--font-noto-sans-kr',
  display: 'swap',
  preload: false,
});

export const metadata: Metadata = {
  title: 'AI 포털',
  description: '사용자 포털 (orchestration-v3)',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // next-themes가 html.class를 토글하므로 suppressHydrationWarning 필수. 폰트 변수는 body에.
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className={`${notoSansKR.variable} antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
