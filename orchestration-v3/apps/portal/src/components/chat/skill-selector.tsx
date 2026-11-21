'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronDown, Plus, Search, Sparkles } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { skillsApi, type Skill } from '@/api/skills';
import { useChatStore } from '@/stores/chat-store';

// 스킬(지침 프리셋) 선택 (ADR-0024) — 활성 스킬 본문이 chat system prompt에 합성된다.
// 멀티셀렉트: 항목 선택 시 메뉴를 닫지 않고 토글. 검색·새 스킬 만들기는 claude.ai 컴포저 참고(§4).
export function SkillSelector() {
  const router = useRouter();
  const [skills, setSkills] = React.useState<Skill[]>([]);
  const [query, setQuery] = React.useState('');
  const selected = useChatStore((s) => s.selectedSkillIds);
  const setSelected = useChatStore((s) => s.setSelectedSkillIds);
  const sending = useChatStore((s) => s.sending);

  React.useEffect(() => {
    skillsApi.list().then(setSkills).catch(() => {});
  }, []);

  function toggle(id: string) {
    setSelected(
      selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]
    );
  }

  const count = selected.length;
  const q = query.trim().toLowerCase();
  const filtered = q
    ? skills.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          (s.description ?? '').toLowerCase().includes(q)
      )
    : skills;

  return (
    <DropdownMenu onOpenChange={(open) => !open && setQuery('')}>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          disabled={sending}
          className={`flex h-8 items-center gap-1 rounded-md px-2 text-xs transition hover:bg-accent disabled:opacity-50 ${
            count > 0 ? 'text-indigo-600 dark:text-indigo-400' : 'text-muted-foreground'
          }`}
        >
          <Sparkles className="size-3.5" />
          <span className="max-w-[120px] truncate">{count > 0 ? `스킬 ${count}` : '스킬'}</span>
          <ChevronDown className="size-3.5" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        {/* 검색 — 키 입력이 드롭다운 타입어헤드로 새지 않게 전파 차단 (§4 mockup 🔍) */}
        <div className="flex items-center gap-2 px-2 pb-1.5">
          <Search className="size-3.5 shrink-0 text-muted-foreground" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            placeholder="검색…"
            className="w-full bg-transparent text-xs outline-none placeholder:text-muted-foreground"
          />
        </div>
        <DropdownMenuSeparator />
        <div className="max-h-60 overflow-y-auto">
          {filtered.length === 0 && (
            <p className="px-2 py-3 text-center text-xs text-muted-foreground">
              {skills.length === 0 ? '아직 스킬이 없습니다.' : '검색 결과가 없습니다.'}
            </p>
          )}
          {filtered.map((s) => (
            <DropdownMenuItem
              key={s.id}
              className="items-start gap-2"
              onSelect={(e) => {
                e.preventDefault();
                toggle(s.id);
              }}
            >
              <span
                className={`mt-0.5 size-3.5 shrink-0 rounded-sm border ${
                  selected.includes(s.id) ? 'bg-indigo-500 border-indigo-500' : 'border-input'
                }`}
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate">{s.name}</span>
                {s.description && (
                  <span className="block truncate text-xs text-muted-foreground">
                    {s.description}
                  </span>
                )}
              </span>
            </DropdownMenuItem>
          ))}
        </div>
        <DropdownMenuSeparator />
        {count > 0 && (
          <DropdownMenuItem onSelect={() => setSelected([])}>모두 해제</DropdownMenuItem>
        )}
        <DropdownMenuItem onSelect={() => router.push('/skills')}>
          <Plus className="size-3.5" /> 새 스킬 만들기
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
