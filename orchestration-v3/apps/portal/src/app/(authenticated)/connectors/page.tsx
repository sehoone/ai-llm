'use client';

import * as React from 'react';
import { toast } from 'sonner';
import { Plug, Plus, Trash2, Wrench } from 'lucide-react';
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
import { connectorsApi, type Connector, type ConnectorTool } from '@/api/connectors';

// 커넥터(사내 MCP 서버) 관리 (ADR-0022). 등록·미리보기까지 — 라이브 대화 tool-calling은 후속.
export default function ConnectorsPage() {
  const [connectors, setConnectors] = React.useState<Connector[]>([]);
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState('');
  const [desc, setDesc] = React.useState('');
  const [url, setUrl] = React.useState('');
  const [cred, setCred] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<Connector | null>(null);
  const [tools, setTools] = React.useState<Record<string, ConnectorTool[]>>({});

  const load = React.useCallback(async () => {
    try {
      setConnectors(await connectorsApi.list());
    } catch {
      toast.error('커넥터 목록을 불러오지 못했습니다.');
    }
  }, []);
  React.useEffect(() => {
    load();
  }, [load]);

  async function create() {
    if (!name.trim() || !url.trim()) {
      toast.error('이름과 MCP URL은 필수입니다.');
      return;
    }
    setSaving(true);
    try {
      const c = await connectorsApi.create({
        name: name.trim(),
        description: desc.trim() || undefined,
        mcp_url: url.trim(),
        credential_ref: cred.trim() || undefined,
      });
      setConnectors((prev) => [c, ...prev]);
      setOpen(false);
      setName('');
      setDesc('');
      setUrl('');
      setCred('');
      toast.success('커넥터를 추가했습니다.');
    } catch {
      toast.error('추가에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    try {
      await connectorsApi.remove(id);
      setConnectors((prev) => prev.filter((c) => c.id !== id));
    } catch {
      toast.error('삭제하지 못했습니다.');
    }
  }

  async function toggleEnabled(c: Connector) {
    try {
      const updated = await connectorsApi.update(c.id, { enabled: !c.enabled });
      setConnectors((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch {
      toast.error('상태 변경에 실패했습니다.');
    }
  }

  async function preview(id: string) {
    try {
      const items = await connectorsApi.previewTools(id);
      setTools((prev) => ({ ...prev, [id]: items }));
      if (items.length === 0) {
        toast.message('도구가 없거나 MCP 서버에 연결하지 못했습니다.');
      }
    } catch {
      toast.error('도구 미리보기에 실패했습니다.');
    }
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl p-6">
        <header className="mb-1 flex items-center gap-3">
          <h1 className="flex-1 text-xl font-semibold">커넥터</h1>
          <Button onClick={() => setOpen((v) => !v)}>
            <Plus /> 커넥터 추가
          </Button>
        </header>
        <p className="mb-6 text-sm text-muted-foreground">
          사내 MCP 서버를 등록해 챗 도구를 확장합니다. 외부 도구는 실행 전 승인(HITL)을 거칩니다.
        </p>

        {open && (
          <div className="mb-6 space-y-3 rounded-xl border border-border bg-card p-4">
            <Input placeholder="이름" value={name} onChange={(e) => setName(e.target.value)} />
            <Input
              placeholder="설명 (선택)"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
            />
            <Input
              placeholder="MCP URL (예: http://mcp-server/mcp)"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <Input
              placeholder="API 키 참조 (sk-… 선택)"
              value={cred}
              onChange={(e) => setCred(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setOpen(false)} disabled={saving}>
                취소
              </Button>
              <Button onClick={create} disabled={saving}>
                추가
              </Button>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {connectors.map((c) => (
            <div key={c.id} className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-start gap-2">
                <Plug className={`size-5 shrink-0 ${c.enabled ? 'text-indigo-500' : 'text-muted-foreground'}`} />
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">{c.name}</div>
                  <div className="truncate text-xs text-muted-foreground">{c.mcp_url}</div>
                </div>
                <Button size="sm" variant="ghost" onClick={() => preview(c.id)} aria-label="도구 미리보기">
                  <Wrench className="size-4" />
                </Button>
                <Button size="sm" variant="outline" onClick={() => toggleEnabled(c)}>
                  {c.enabled ? '사용 중' : '사용 안 함'}
                </Button>
                <button
                  onClick={() => setDeleteTarget(c)}
                  className="text-muted-foreground transition hover:text-destructive"
                  aria-label="삭제"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
              {tools[c.id] && tools[c.id].length > 0 && (
                <ul className="mt-3 space-y-1 border-t border-border pt-3 text-xs">
                  {tools[c.id].map((t) => (
                    <li key={t.name} className="flex items-center gap-2">
                      <span className="font-mono">{t.name}</span>
                      <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                        {t.risk}
                      </span>
                      <span className="truncate text-muted-foreground">{t.description}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
        {connectors.length === 0 && !open && (
          <p className="py-16 text-center text-sm text-muted-foreground">
            아직 커넥터가 없습니다. &ldquo;커넥터 추가&rdquo;로 사내 MCP 서버를 등록하세요.
          </p>
        )}

        <AlertDialog open={deleteTarget !== null} onOpenChange={(o) => !o && setDeleteTarget(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>커넥터를 삭제할까요?</AlertDialogTitle>
              <AlertDialogDescription>
                &ldquo;{deleteTarget?.name}&rdquo; 커넥터가 영구 삭제됩니다.
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
