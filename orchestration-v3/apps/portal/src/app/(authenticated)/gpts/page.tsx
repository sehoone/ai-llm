'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Bot, Plus, Trash2 } from 'lucide-react';
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
import { gptsApi, type CustomGpt } from '@/api/gpts';

export default function GptsPage() {
  const router = useRouter();
  const [gpts, setGpts] = React.useState<CustomGpt[]>([]);
  const [creating, setCreating] = React.useState(false);
  const [name, setName] = React.useState('');
  const [desc, setDesc] = React.useState('');
  const [instructions, setInstructions] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<CustomGpt | null>(null);

  const load = React.useCallback(async () => {
    try {
      setGpts(await gptsApi.list());
    } catch {
      toast.error('GPT 목록을 불러오지 못했습니다.');
    }
  }, []);
  React.useEffect(() => {
    load();
  }, [load]);

  async function create() {
    if (!name.trim() || !instructions.trim()) {
      toast.error('이름과 지침은 필수입니다.');
      return;
    }
    setSaving(true);
    try {
      const g = await gptsApi.create({
        name: name.trim(),
        description: desc.trim() || undefined,
        instructions: instructions.trim(),
      });
      setGpts((prev) => [g, ...prev]);
      setCreating(false);
      setName('');
      setDesc('');
      setInstructions('');
      toast.success('GPT를 만들었습니다.');
    } catch {
      toast.error('GPT 생성에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    try {
      await gptsApi.remove(id);
      setGpts((prev) => prev.filter((g) => g.id !== id));
    } catch {
      toast.error('삭제하지 못했습니다.');
    }
  }

  usePageHeader(
    {
      title: '커스텀 GPT',
      actions: (
        <Button size="sm" onClick={() => setCreating((v) => !v)}>
          <Plus /> 새 GPT
        </Button>
      ),
    },
    []
  );

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl p-6">
      {creating && (
        <div className="mb-6 space-y-3 rounded-xl border border-border bg-card p-4">
          <Input placeholder="이름" value={name} onChange={(e) => setName(e.target.value)} />
          <Input placeholder="설명 (선택)" value={desc} onChange={(e) => setDesc(e.target.value)} />
          <Textarea
            placeholder="지침 (시스템 프롬프트) — 이 GPT가 어떻게 행동할지 적어주세요."
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
        {gpts.map((g) => (
          <div
            key={g.id}
            className="group/card flex flex-col rounded-xl border border-border bg-card p-4"
          >
            <div className="mb-1 flex items-start gap-2">
              <Bot className="size-5 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1 truncate font-medium">{g.name}</div>
              <button
                onClick={() => setDeleteTarget(g)}
                className="text-muted-foreground opacity-0 transition hover:text-destructive group-hover/card:opacity-100"
                aria-label="삭제"
              >
                <Trash2 className="size-4" />
              </button>
            </div>
            {g.description && (
              <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">{g.description}</p>
            )}
            <Button
              variant="outline"
              size="sm"
              className="mt-auto"
              onClick={() => router.push(`/gpts/${g.id}`)}
            >
              사용하기
            </Button>
          </div>
        ))}
      </div>
      {gpts.length === 0 && !creating && (
        <p className="py-16 text-center text-sm text-muted-foreground">
          아직 커스텀 GPT가 없습니다. &ldquo;새 GPT&rdquo;로 만들어보세요.
        </p>
      )}

      <AlertDialog open={deleteTarget !== null} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>GPT를 삭제할까요?</AlertDialogTitle>
            <AlertDialogDescription>
              &ldquo;{deleteTarget?.name}&rdquo;와 관련 세션이 영구 삭제됩니다.
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
