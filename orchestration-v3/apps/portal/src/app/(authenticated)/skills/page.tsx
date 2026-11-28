'use client';

import * as React from 'react';
import { toast } from 'sonner';
import {
  Braces,
  Brain,
  Briefcase,
  FileText,
  Languages,
  type LucideIcon,
  MessageSquare,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { usePageHeader } from '@/hooks/use-page-header';
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

// 선택 가능한 아이콘·색상 (백엔드 skill.icon/color — 기본 'sparkles'/'#6366f1').
const ICONS: Record<string, LucideIcon> = {
  sparkles: Sparkles,
  code: Braces,
  document: FileText,
  message: MessageSquare,
  language: Languages,
  brain: Brain,
  business: Briefcase,
};
const ICON_NAMES = Object.keys(ICONS);
const COLORS = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#8b5cf6'];

function SkillIcon({ name, className, color }: { name: string; className?: string; color?: string }) {
  const Icon = ICONS[name] ?? Sparkles;
  return <Icon className={className} style={color ? { color } : undefined} />;
}

// 스킬(지침 프리셋) 관리 (ADR-0024). 컴포저의 스킬 칩에서 활성화해 chat system prompt에 합성.
export default function SkillsPage() {
  const [skills, setSkills] = React.useState<Skill[]>([]);
  const [editing, setEditing] = React.useState<Skill | null>(null);
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState('');
  const [desc, setDesc] = React.useState('');
  const [body, setBody] = React.useState('');
  const [icon, setIcon] = React.useState('sparkles');
  const [color, setColor] = React.useState(COLORS[0]);
  const [saving, setSaving] = React.useState(false);
  const [importing, setImporting] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<Skill | null>(null);
  const importRef = React.useRef<HTMLInputElement>(null);

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
    setIcon('sparkles');
    setColor(COLORS[0]);
    setOpen(true);
  }
  function openEdit(s: Skill) {
    setEditing(s);
    setName(s.name);
    setDesc(s.description || '');
    setBody(s.body);
    setIcon(s.icon || 'sparkles');
    setColor(s.color || COLORS[0]);
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
          icon,
          color,
        });
        setSkills((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      } else {
        const created = await skillsApi.create({
          name: name.trim(),
          description: desc.trim() || undefined,
          body: body.trim(),
          icon,
          color,
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

  // SKILL.md / .md / .txt / .zip 업로드 → 스킬 생성 (ADR-0024 · claude.ai 참고).
  async function onImport(files: FileList | null) {
    if (!files || files.length === 0) return;
    setImporting(true);
    try {
      for (const f of Array.from(files)) {
        const created = await skillsApi.importFile(f);
        setSkills((prev) => [created, ...prev]);
      }
      toast.success('스킬을 가져왔습니다.');
    } catch {
      toast.error('가져오기에 실패했습니다. (SKILL.md · .md · .txt · .zip만 지원)');
    } finally {
      setImporting(false);
      if (importRef.current) importRef.current.value = '';
    }
  }

  usePageHeader(
    {
      title: '스킬',
      actions: (
        <>
          <Button
            variant="outline"
            size="sm"
            onClick={() => importRef.current?.click()}
            disabled={importing}
          >
            <Upload /> 가져오기
          </Button>
          <Button size="sm" onClick={openNew}>
            <Plus /> 새 스킬
          </Button>
        </>
      ),
    },
    [importing]
  );

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl p-6">
        <input
          ref={importRef}
          type="file"
          multiple
          accept=".md,.txt,.zip,text/markdown,text/plain,application/zip"
          className="hidden"
          onChange={(e) => onImport(e.target.files)}
        />
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
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-muted-foreground">아이콘</span>
                {ICON_NAMES.map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setIcon(n)}
                    aria-label={n}
                    className={`rounded-md border p-1.5 transition hover:bg-accent ${
                      icon === n ? 'border-ring bg-accent' : 'border-transparent'
                    }`}
                  >
                    <SkillIcon name={n} className="size-4" color={color} />
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-muted-foreground">색상</span>
                {COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColor(c)}
                    aria-label={c}
                    className={`size-5 rounded-full transition ${
                      color === c ? 'ring-2 ring-offset-2 ring-offset-card' : ''
                    }`}
                    style={{ backgroundColor: c, ...(color === c ? { boxShadow: `0 0 0 2px ${c}` } : {}) }}
                  />
                ))}
              </div>
            </div>
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
                <SkillIcon name={s.icon} className="size-5 shrink-0" color={s.color} />
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
