'use client';

import * as React from 'react';
import { toast } from 'sonner';
import { Pencil, Plus, Sparkles, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
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
import { skillsApi, type Skill } from '@/api/skills';

// 스킬(지침 프리셋) 관리 (ADR-0024). 컴포저의 스킬 칩에서 활성화해 chat system prompt에 합성.
export default function SkillsPage() {
  const [skills, setSkills] = React.useState<Skill[]>([]);
  const [editing, setEditing] = React.useState<Skill | null>(null);
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState('');
  const [desc, setDesc] = React.useState('');
  const [body, setBody] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<Skill | null>(null);

  const load = React.useCallback(async () => {
    try {
      setSkills(await skillsApi.list());
    } catch {
      toast.error('스킬 목록을 불러오지 못했습니다.');
    }
  }, []);
  React.useEffect(() => {
    load();
  }, [load]);

  function openNew() {
    setEditing(null);
    setName('');
    setDesc('');
    setBody('');
    setOpen(true);
  }
  function openEdit(s: Skill) {
    setEditing(s);
    setName(s.name);
    setDesc(s.description || '');
    setBody(s.body);
    setOpen(true);
  }

  async function save() {
    if (!name.trim() || !body.trim()) {
      toast.error('이름과 지침 본문은 필수입니다.');
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        const updated = await skillsApi.update(editing.id, {
          name: name.trim(),
          description: desc.trim() || undefined,
          body: body.trim(),
        });
        setSkills((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      } else {
        const created = await skillsApi.create({
          name: name.trim(),
          description: desc.trim() || undefined,
          body: body.trim(),
        });
        setSkills((prev) => [created, ...prev]);
      }
      setOpen(false);
      toast.success('스킬을 저장했습니다.');
    } catch {
      toast.error('저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    try {
      await skillsApi.remove(id);
      setSkills((prev) => prev.filter((s) => s.id !== id));
    } catch {
      toast.error('삭제하지 못했습니다.');
    }
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl p-6">
        <header className="mb-1 flex items-center gap-3">
          <h1 className="flex-1 text-xl font-semibold">스킬</h1>
          <Button onClick={openNew}>
            <Plus /> 새 스킬
          </Button>
        </header>
        <p className="mb-6 text-sm text-muted-foreground">
          재사용 지침 프리셋. 채팅 입력창의 스킬에서 켜면 해당 지침이 대화에 적용됩니다.
        </p>

        {open && (
          <div className="mb-6 space-y-3 rounded-xl border border-border bg-card p-4">
            <Input placeholder="이름" value={name} onChange={(e) => setName(e.target.value)} />
            <Input
              placeholder="설명 (선택)"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
            />
            <Textarea
              placeholder="지침 본문 — 예: '항상 정중한 비즈니스 톤으로 답하라.'"
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setOpen(false)} disabled={saving}>
                취소
              </Button>
              <Button onClick={save} disabled={saving}>
                저장
              </Button>
            </div>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          {skills.map((s) => (
            <div
              key={s.id}
              className="group/card flex flex-col rounded-xl border border-border bg-card p-4"
            >
              <div className="mb-1 flex items-start gap-2">
                <Sparkles className="size-5 shrink-0" style={{ color: s.color }} />
                <div className="min-w-0 flex-1 truncate font-medium">{s.name}</div>
                <button
                  onClick={() => openEdit(s)}
                  className="text-muted-foreground opacity-0 transition hover:text-foreground group-hover/card:opacity-100"
                  aria-label="수정"
                >
                  <Pencil className="size-4" />
                </button>
                <button
                  onClick={() => setDeleteTarget(s)}
                  className="text-muted-foreground opacity-0 transition hover:text-destructive group-hover/card:opacity-100"
                  aria-label="삭제"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
              {s.description && (
                <p className="line-clamp-2 text-sm text-muted-foreground">{s.description}</p>
              )}
            </div>
          ))}
        </div>
        {skills.length === 0 && !open && (
          <p className="py-16 text-center text-sm text-muted-foreground">
            아직 스킬이 없습니다. &ldquo;새 스킬&rdquo;로 만들어보세요.
          </p>
        )}

        <AlertDialog open={deleteTarget !== null} onOpenChange={(o) => !o && setDeleteTarget(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>스킬을 삭제할까요?</AlertDialogTitle>
              <AlertDialogDescription>
                &ldquo;{deleteTarget?.name}&rdquo; 스킬이 영구 삭제됩니다.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>취소</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => {
                  if (deleteTarget) remove(deleteTarget.id);
                  setDeleteTarget(null);
                }}
              >
                삭제
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}
