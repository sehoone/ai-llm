'use client';

import * as React from 'react';
import { ChevronDown, Sparkles } from 'lucide-react';
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
// 멀티셀렉트: 항목 선택 시 메뉴를 닫지 않고 토글. 스킬이 없으면 미표시.
export function SkillSelector() {
  const [skills, setSkills] = React.useState<Skill[]>([]);
  const selected = useChatStore((s) => s.selectedSkillIds);
  const setSelected = useChatStore((s) => s.setSelectedSkillIds);
  const sending = useChatStore((s) => s.sending);

  React.useEffect(() => {
    skillsApi.list().then(setSkills).catch(() => {});
  }, []);

  if (skills.length === 0) return null;

  function toggle(id: string) {
    setSelected(
      selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]
    );
  }

  const count = selected.length;

  return (
    <DropdownMenu>
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
      <DropdownMenuContent align="start" className="max-h-72 w-56 overflow-y-auto">
        {skills.map((s) => (
          <DropdownMenuItem
            key={s.id}
            onSelect={(e) => {
              e.preventDefault();
              toggle(s.id);
            }}
          >
            <span
              className={`size-3.5 shrink-0 rounded-sm border ${
                selected.includes(s.id) ? 'bg-indigo-500 border-indigo-500' : 'border-input'
              }`}
            />
            <span className="min-w-0 flex-1 truncate">{s.name}</span>
          </DropdownMenuItem>
        ))}
        {count > 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => setSelected([])}>모두 해제</DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
