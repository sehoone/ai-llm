'use client';

import * as React from 'react';
import { useTheme } from 'next-themes';
import { toast } from 'sonner';
import { Monitor, Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { userApi, type Me } from '@/api/user';
import { chatApi } from '@/api/chat';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="mb-4 text-sm font-semibold">{title}</h2>
      {children}
    </section>
  );
}

const THEMES = [
  { value: 'light', label: '라이트', icon: Sun },
  { value: 'dark', label: '다크', icon: Moon },
  { value: 'system', label: '시스템', icon: Monitor },
];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  const [me, setMe] = React.useState<Me | null>(null);
  const [username, setUsername] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [savingProfile, setSavingProfile] = React.useState(false);

  const [curPw, setCurPw] = React.useState('');
  const [newPw, setNewPw] = React.useState('');
  const [confirmPw, setConfirmPw] = React.useState('');
  const [savingPw, setSavingPw] = React.useState(false);

  const [memoryConfirm, setMemoryConfirm] = React.useState(false);

  React.useEffect(() => setMounted(true), []);
  React.useEffect(() => {
    userApi
      .me()
      .then((m) => {
        setMe(m);
        setUsername(m.username);
        setEmail(m.email);
      })
      .catch(() => toast.error('프로필을 불러오지 못했습니다.'));
  }, []);

  async function saveProfile() {
    if (!username.trim()) {
      toast.error('아이디는 비울 수 없습니다.');
      return;
    }
    setSavingProfile(true);
    try {
      const body: { username?: string; email?: string } = {};
      if (me && username.trim() !== me.username) body.username = username.trim();
      if (me && email.trim() !== me.email) body.email = email.trim();
      if (Object.keys(body).length === 0) {
        toast.message('변경 사항이 없습니다.');
        return;
      }
      const updated = await userApi.updateMe(body);
      setMe(updated);
      toast.success('프로필을 저장했습니다.');
    } catch {
      toast.error('저장에 실패했습니다. (중복된 아이디/이메일일 수 있습니다)');
    } finally {
      setSavingProfile(false);
    }
  }

  async function changePassword() {
    if (newPw.length < 8) {
      toast.error('새 비밀번호는 8자 이상이어야 합니다.');
      return;
    }
    if (newPw !== confirmPw) {
      toast.error('새 비밀번호가 일치하지 않습니다.');
      return;
    }
    setSavingPw(true);
    try {
      await userApi.changePassword(curPw, newPw);
      setCurPw('');
      setNewPw('');
      setConfirmPw('');
      toast.success('비밀번호를 변경했습니다.');
    } catch {
      toast.error('변경 실패 — 현재 비밀번호를 확인하세요.');
    } finally {
      setSavingPw(false);
    }
  }

  async function clearMemory() {
    try {
      await chatApi.deleteMemory();
      toast.success('장기 메모리를 삭제했습니다.');
    } catch {
      toast.error('메모리 삭제에 실패했습니다.');
    }
  }

  const field = 'w-full';

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-2xl p-6">
        <header className="mb-6">
          <h1 className="text-xl font-semibold">설정</h1>
        </header>

        <div className="space-y-5">
        <Section title="프로필">
          <div className="space-y-3">
            <div className="space-y-1">
              <label htmlFor="username" className="text-xs text-muted-foreground">
                아이디
              </label>
              <Input
                id="username"
                className={field}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="email" className="text-xs text-muted-foreground">
                이메일
              </label>
              <Input
                id="email"
                type="email"
                className={field}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            {me && <p className="text-xs text-muted-foreground">역할: {me.role}</p>}
            <div className="flex justify-end">
              <Button onClick={saveProfile} disabled={savingProfile || !me}>
                저장
              </Button>
            </div>
          </div>
        </Section>

        <Section title="비밀번호 변경">
          <div className="space-y-3">
            <Input
              type="password"
              placeholder="현재 비밀번호"
              autoComplete="current-password"
              value={curPw}
              onChange={(e) => setCurPw(e.target.value)}
            />
            <Input
              type="password"
              placeholder="새 비밀번호 (8자 이상)"
              autoComplete="new-password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
            />
            <Input
              type="password"
              placeholder="새 비밀번호 확인"
              autoComplete="new-password"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
            />
            <div className="flex justify-end">
              <Button onClick={changePassword} disabled={savingPw || !curPw || !newPw}>
                변경
              </Button>
            </div>
          </div>
        </Section>

        <Section title="테마">
          <div className="flex gap-2">
            {THEMES.map((t) => {
              const Icon = t.icon;
              const active = mounted && theme === t.value;
              return (
                <Button
                  key={t.value}
                  variant={active ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTheme(t.value)}
                >
                  <Icon className="size-4" /> {t.label}
                </Button>
              );
            })}
          </div>
        </Section>

        <Section title="장기 메모리">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              대화에서 학습된 장기 메모리를 모두 삭제합니다.
            </p>
            <Button variant="outline" onClick={() => setMemoryConfirm(true)}>
              삭제
            </Button>
          </div>
        </Section>
        </div>
      </div>

      <AlertDialog open={memoryConfirm} onOpenChange={setMemoryConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>장기 메모리를 삭제할까요?</AlertDialogTitle>
            <AlertDialogDescription>
              저장된 모든 장기 메모리가 영구 삭제됩니다. 되돌릴 수 없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                clearMemory();
                setMemoryConfirm(false);
              }}
            >
              삭제
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
