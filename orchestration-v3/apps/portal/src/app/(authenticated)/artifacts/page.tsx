'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Plus, Search as SearchIcon, Shapes } from 'lucide-react';
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
import { Button } from '@/components/ui/button';
import { ArtifactCard } from '@/components/artifacts/artifact-card';
import { ArtifactViewPanel } from '@/components/artifacts/artifact-view-panel';
import { ArtifactEditor } from '@/components/artifacts/artifact-editor';
import { artifactApi, type ArtifactDetail, type ArtifactSummary } from '@/api/artifacts';
import { chatApi } from '@/api/chat';
import { usePageHeader } from '@/hooks/use-page-header';
import { useChat } from '@/hooks/use-chat';

const TYPE_FILTERS: { value: string; label: string }[] = [
  { value: 'all', label: '전체 타입' },
  { value: 'text/html', label: 'HTML' },
  { value: 'application/vnd.react', label: 'React' },
  { value: 'image/svg+xml', label: 'SVG' },
  { value: 'application/vnd.mermaid', label: 'Mermaid' },
  { value: 'text/markdown', label: 'Markdown' },
  { value: 'application/vnd.code', label: 'Code' },
];

export default function ArtifactsPage() {
  const router = useRouter();
  const { selectSession } = useChat();

  const [artifacts, setArtifacts] = React.useState<ArtifactSummary[]>([]);
  const [sessionNames, setSessionNames] = React.useState<Record<string, string>>({});
  const [loading, setLoading] = React.useState(true);
  const [selected, setSelected] = React.useState<ArtifactDetail | null>(null);
  const [opening, setOpening] = React.useState(false);
  const [creating, setCreating] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const [typeFilter, setTypeFilter] = React.useState('all');
  const [publishedOnly, setPublishedOnly] = React.useState(false);
  const [toDelete, setToDelete] = React.useState<ArtifactSummary | null>(null);

  React.useEffect(() => {
    artifactApi
      .listAll()
      .then(setArtifacts)
      .catch(() => toast.error('아티팩트 목록을 불러오지 못했습니다.'))
      .finally(() => setLoading(false));
    chatApi
      .listSessions()
      .then((sessions) => {
        const map: Record<string, string> = {};
        for (const s of sessions) map[String(s.id)] = s.title || '새 대화';
        setSessionNames(map);
      })
      .catch(() => {});
  }, []);

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    return artifacts.filter((a) => {
      if (typeFilter !== 'all' && a.artifact_type !== typeFilter) return false;
      if (publishedOnly && !a.is_published) return false;
      if (q && !(a.title || a.identifier).toLowerCase().includes(q)) return false;
      return true;
    });
  }, [artifacts, search, typeFilter, publishedOnly]);

  async function handleSelect(summary: ArtifactSummary) {
    setCreating(false);
    setOpening(true);
    try {
      setSelected(await artifactApi.get(summary.id));
    } catch {
      toast.error('아티팩트를 불러오지 못했습니다.');
    } finally {
      setOpening(false);
    }
  }

  function handleCreated(detail: ArtifactDetail) {
    setArtifacts((prev) => [detail, ...prev]);
    setSelected(detail);
    setCreating(false);
  }

  async function handleDelete() {
    if (!toDelete) return;
    try {
      await artifactApi.remove(toDelete.id);
      setArtifacts((prev) => prev.filter((a) => a.id !== toDelete.id));
      if (selected?.id === toDelete.id) setSelected(null);
      toast.success('아티팩트를 삭제했습니다.');
    } catch {
      toast.error('삭제에 실패했습니다.');
    } finally {
      setToDelete(null);
    }
  }

  function openOriginalChat() {
    if (!selected) return;
    const sid = Number(selected.session_id);
    if (!Number.isNaN(sid)) selectSession(sid);
    router.push('/chat');
  }

  usePageHeader(
    {
      title: (
        <span className="flex items-center gap-2">
          <Shapes className="size-4" /> 아티팩트
        </span>
      ),
      actions: (
        <Button
          size="sm"
          onClick={() => {
            setSelected(null);
            setCreating(true);
          }}
        >
          <Plus className="size-4" /> 새 아티팩트
        </Button>
      ),
    },
    []
  );

  return (
    <div className="flex min-h-0 flex-1 gap-4 p-4">
      {/* 왼쪽 — 라이브러리 목록 */}
      <div className="flex w-full flex-col gap-3 sm:w-72 lg:w-80">
        <label className="flex h-10 items-center rounded-md border border-border ps-2">
          <SearchIcon className="me-2 size-4 text-muted-foreground" />
          <input
            type="text"
            className="w-full flex-1 bg-inherit text-sm outline-none"
            placeholder="아티팩트 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>

        <div className="flex items-center gap-2">
          <select
            className="flex-1 rounded-md border border-border bg-background px-2 py-1.5 text-xs"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            {TYPE_FILTERS.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-1 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={publishedOnly}
              onChange={(e) => setPublishedOnly(e.target.checked)}
            />
            공개됨
          </label>
        </div>

        <div className="flex-1 space-y-2 overflow-y-auto pe-1">
          {filtered.map((a) => (
            <ArtifactCard
              key={a.id}
              artifact={a}
              sessionName={sessionNames[a.session_id]}
              selected={selected?.id === a.id}
              onClick={() => handleSelect(a)}
              onDelete={() => setToDelete(a)}
            />
          ))}
          {!loading && filtered.length === 0 && (
            <div className="py-8 text-center text-sm text-muted-foreground">
              {artifacts.length === 0
                ? '아직 아티팩트가 없습니다. 대화에서 문서·코드를 만들면 여기에 모입니다.'
                : '조건에 맞는 아티팩트가 없습니다.'}
            </div>
          )}
          {loading && (
            <div className="py-8 text-center text-sm text-muted-foreground">불러오는 중…</div>
          )}
        </div>
      </div>

      {/* 오른쪽 — 미리보기 / 에디터 */}
      <div className="hidden min-w-0 flex-1 flex-col md:flex">
        {creating ? (
          <ArtifactEditor onCreated={handleCreated} onCancel={() => setCreating(false)} />
        ) : selected ? (
          <ArtifactViewPanel
            artifact={selected}
            onClose={() => setSelected(null)}
            // standalone(세션 0) 아티팩트는 원본 대화가 없으므로 버튼 숨김.
            onOpenChat={Number(selected.session_id) > 0 ? openOriginalChat : undefined}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border text-muted-foreground">
            <Shapes className="size-10" />
            <p className="text-sm">{opening ? '불러오는 중…' : '왼쪽에서 아티팩트를 선택하세요'}</p>
          </div>
        )}
      </div>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>아티팩트 삭제</AlertDialogTitle>
            <AlertDialogDescription>
              &lsquo;{toDelete?.title || toDelete?.identifier}&rsquo; 아티팩트와 모든 버전을 삭제합니다.
              되돌릴 수 없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>삭제</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
