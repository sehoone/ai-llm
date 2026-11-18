'use client';

import * as React from 'react';
import { useTheme } from 'next-themes';
import { Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);

  // 마운트 전에는 테마를 알 수 없음 → 하이드레이션 불일치 방지용 빈 버튼.
  if (!mounted) {
    return <Button variant="ghost" size="icon" aria-label="테마 전환" />;
  }

  const isDark = resolvedTheme === 'dark';
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      aria-label="테마 전환"
    >
      {isDark ? <Sun /> : <Moon />}
    </Button>
  );
}
