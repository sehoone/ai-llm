'use client';

import * as React from 'react';
import { toast } from 'sonner';
import { Share2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ArtifactRenderer } from '@/components/chat/artifact-renderer';
import { artifactApi } from '@/api/artifacts';
import { useArtifactStore } from '@/stores/artifact-store';

export function ArtifactPanel() {
  const art = useArtifactStore((s) => (s.activeId ? s.artifacts[s.activeId] : undefined));
  const closePanel = useArtifactStore((s) => s.closePanel);
  const setContent = useArtifactStore((s) => s.setContent);
  const setPublished = useArtifactStore((s) => s.setPublished);
  const [publishing, setPublishing] = React.useState(false);

  // 히스토리에서 연 아티팩트: content 없고 DB id 있으면 상세 지연 로드.
  const needLoad = !!art && !!art.id && !art.content;
  React.useEffect(() => {
    if (!art || !art.id || art.content) return;
    artifactApi
      .get(art.id)
      .then((d) => setContent(art.identifier, d.content))
      .catch(() => {});
  }, [art, needLoad, setContent]);

  if (!art) return null;

  async function share() {
    if (!art) return;
    if (!art.id) {
      toast.error('아직 저장 중입니다. 잠시 후 다시 시도하세요.');
      return;
    }
    setPublishing(true);
    try {
      const token = art.publicToken || (await artifactApi.publish(art.id));
      if (!art.publicToken) setPublished(art.identifier, token);
      await navigator.clipboard.writeText(`${window.location.origin}/artifact/${token}`);
      toast.success('공개 링크를 복사했습니다.');
    } catch {
      toast.error('공유 링크 생성에 실패했습니다.');
    } finally {
      setPublishing(false);
    }
  }

  return (
    <aside className="fixed inset-0 z-40 flex flex-col border-s border-border bg-background md:static md:inset-auto md:w-[460px] md:shrink-0">
      <header className="flex items-center gap-2 border-b border-border px-3 py-2">
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium">{art.title}</div>
          <div className="truncate text-xs text-muted-foreground">{art.type}</div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={share}
          disabled={publishing || !art.id}
          aria-label="공유 링크"
          title={art.isPublished ? '공개됨 — 링크 복사' : '공개 링크 생성'}
        >
          <Share2 className="size-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={closePanel} aria-label="닫기">
          <X className="size-4" />
        </Button>
      </header>
      <div className="min-h-0 flex-1">
        <ArtifactRenderer type={art.type} content={art.content} complete={art.complete} />
      </div>
    </aside>
  );
}
