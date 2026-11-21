'use client';

import * as React from 'react';
import Link from 'next/link';
import { useTheme } from 'next-themes';
import { toast } from 'sonner';
import { Database, KeyRound, Monitor, Moon, Palette, Plug, Sparkles, Sun, User } from 'lucide-react';
import { cn } from '@/lib/utils';
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

const THEMES = [
  { value: 'light', label: '라이트', icon: Sun },
  { value: 'dark', label: '다크', icon: Moon },
  { value: 'system', label: '시스템', icon: Monitor },
];

const TABS = [
  { id: 'profile', label: '프로필', icon: User },
  { id: 'security', label: '보안', icon: KeyRound },
  { id: 'integrations', label: '스킬·커넥터', icon: Plug },
  { id: 'appearance', label: '모양', icon: Palette },
  { id: 'data', label: '데이터', icon: Database },
] as const;

type TabId = (typeof TABS)[number]['id'];

// 설정 본문 — claude.ai식 레이어 팝업(SettingsDialog)에서 사용. 왼쪽 탭 사이드바 + 오른쪽 내용 2-pane.
// onNavigate: 내부 링크(스킬·커넥터) 이동 시 팝업을 닫기 위한 콜백.
export function SettingsPanel({ onNavigate }: { onNavigate?: () => void }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  const [tab, setTab] = React.useState<TabId>('profile');

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

  return (
    <div className="flex min-h-0 flex-1">
      {/* 왼쪽 탭 사이드바 */}
      <nav className="w-48 shrink-0 space-y-1 border-e border-border bg-muted/30 p-3">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={cn(
              'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm',
              tab === id
                ? 'bg-accent font-medium text-accent-foreground'
                : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'
            )}
          >
            <Icon className="size-4" /> {label}
          </button>
        ))}
      </nav>

      {/* 오른쪽 내용 */}
      <div className="min-w-0 flex-1 overflow-y-auto p-6">
        {tab === 'profile' && (
          <div className="max-w-md space-y-4">
            <h2 className="text-base font-semibold">프로필</h2>
            <Field label="아이디">
              <Input value={username} onChange={(e) => setUsername(e.target.value)} />
            </Field>
            <Field label="이메일">
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            {me && <p className="text-xs text-muted-foreground">역할: {me.role}</p>}
            <div className="flex justify-end">
              <Button onClick={saveProfile} disabled={savingProfile || !me}>
                저장
              </Button>
            </div>
          </div>
        )}

        {tab === 'security' && (
          <div className="max-w-md space-y-4">
            <h2 className="text-base font-semibold">비밀번호 변경</h2>
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
        )}

        {tab === 'integrations' && (
          <div className="max-w-md space-y-4">
            <h2 className="text-base font-semibold">스킬·커넥터</h2>
            <div className="flex flex-col gap-2">
              <Link
                href="/skills"
                onClick={onNavigate}
                className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-accent"
              >
                <Sparkles className="size-4" /> 스킬 관리 — 재사용 지침 프리셋
              </Link>
              <Link
                href="/connectors"
                onClick={onNavigate}
                className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-accent"
              >
                <Plug className="size-4" /> 커넥터 관리 — 사내 MCP 서버
              </Link>
            </div>
          </div>
        )}

        {tab === 'appearance' && (
          <div className="max-w-md space-y-4">
            <h2 className="text-base font-semibold">테마</h2>
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
          </div>
        )}

        {tab === 'data' && (
          <div className="max-w-md space-y-4">
            <h2 className="text-base font-semibold">장기 메모리</h2>
            <p className="text-sm text-muted-foreground">
              대화에서 학습된 장기 메모리를 모두 삭제합니다. 되돌릴 수 없습니다.
            </p>
            <div className="flex justify-end">
              <Button variant="outline" onClick={() => setMemoryConfirm(true)}>
                삭제
              </Button>
            </div>
          </div>
        )}
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
