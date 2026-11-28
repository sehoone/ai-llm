'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { FolderKanban, Plus, Trash2 } from 'lucide-react';
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
import { projectsApi, type Project } from '@/api/projects';

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [creating, setCreating] = React.useState(false);
  const [name, setName] = React.useState('');
  const [desc, setDesc] = React.useState('');
  const [instructions, setInstructions] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<Project | null>(null);

  const load = React.useCallback(async () => {
    try {
      setProjects(await projectsApi.list());
    } catch {
      toast.error('프로젝트 목록을 불러오지 못했습니다.');
    }
  }, []);
  React.useEffect(() => {
    load();
  }, [load]);

  async function create() {
    if (!name.trim()) {
      toast.error('이름은 필수입니다.');
      return;
    }
    setSaving(true);
    try {
      const p = await projectsApi.create({
        name: name.trim(),
        description: desc.trim() || undefined,
        instructions: instructions.trim() || undefined,
      });
      setProjects((prev) => [p, ...prev]);
      setCreating(false);
      setName('');
      setDesc('');
      setInstructions('');
      toast.success('프로젝트를 만들었습니다.');
    } catch {
      toast.error('프로젝트 생성에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    try {
      await projectsApi.remove(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch {
      toast.error('삭제하지 못했습니다.');
    }
  }

  usePageHeader(
    {
      title: '프로젝트',
      actions: (
        <Button size="sm" onClick={() => setCreating((v) => !v)}>
          <Plus /> 새 프로젝트
        </Button>
      ),
    },
    []
  );

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl p-6">
        <p className="mb-6 text-sm text-muted-foreground">대화·지침·지식을 한 작업공간에 모으세요.</p>

        {creating && (
          <div className="mb-6 space-y-3 rounded-xl border border-border bg-card p-4">
            <Input placeholder="이름" value={name} onChange={(e) => setName(e.target.value)} />
            <Input
              placeholder="설명 (선택)"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
            />
            <Textarea
              placeholder="프로젝트 지침 (선택) — 이 프로젝트의 모든 대화에 적용될 system prompt."
              rows={4}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setCreating(false)} disabled={saving}>
                취소
              </Button>
              <Button onClick={create} disabled={saving}>
                만들기
              </Button>
            </div>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          {projects.map((p) => (
            <div
              key={p.id}
              className="group/card flex flex-col rounded-xl border border-border bg-card p-4"
            >
              <div className="mb-1 flex items-start gap-2">
                <FolderKanban className="size-5 shrink-0" style={{ color: p.color }} />
                <div className="min-w-0 flex-1 truncate font-medium">{p.name}</div>
                <button
                  onClick={() => setDeleteTarget(p)}
                  className="text-muted-foreground opacity-0 transition hover:text-destructive group-hover/card:opacity-100"
                  aria-label="삭제"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
              {p.description && (
                <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">{p.description}</p>
              )}
              <Button
                variant="outline"
                size="sm"
                className="mt-auto"
                onClick={() => router.push(`/projects/${p.id}`)}
              >
                열기
              </Button>
            </div>
          ))}
        </div>
        {projects.length === 0 && !creating && (
          <p className="py-16 text-center text-sm text-muted-foreground">
            아직 프로젝트가 없습니다. &ldquo;새 프로젝트&rdquo;로 만들어보세요.
          </p>
        )}

        <AlertDialog open={deleteTarget !== null} onOpenChange={(o) => !o && setDeleteTarget(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>프로젝트를 삭제할까요?</AlertDialogTitle>
              <AlertDialogDescription>
                &ldquo;{deleteTarget?.name}&rdquo; 프로젝트와 소속 대화·지식이 영구 삭제됩니다.
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
