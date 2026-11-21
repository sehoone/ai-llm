'use client';

import * as React from 'react';
import { Check, Copy, Download, ExternalLink, Share2, X } from 'lucide-react';
import { toast } from 'sonner';
import { artifactApi, type ArtifactDetail } from '@/api/artifacts';
import { ArtifactRenderer } from '@/components/chat/artifact-renderer';
import { VersionSwitcher } from '@/components/artifacts/version-switcher';

const TYPE_LABELS: Record<string, string> = {
  'text/html': 'HTML',
  'application/vnd.react': 'React',
  'image/svg+xml': 'SVG',
  'application/vnd.mermaid': 'Mermaid',
  'text/markdown': 'Markdown',
  'application/vnd.code': 'Code',
};

const TYPE_EXTENSIONS: Record<string, string> = {
  'text/html': 'html',
  'application/vnd.react': 'jsx',
  'image/svg+xml': 'svg',
  'application/vnd.mermaid': 'mmd',
  'text/markdown': 'md',
  'application/vnd.code': 'txt',
};

export function ArtifactViewPanel({
  artifact,
  onClose,
  onOpenChat,
}: {
  artifact: ArtifactDetail;
  onClose: () => void;
  onOpenChat?: () => void;
}) {
  const [copied, setCopied] = React.useState(false);
  const [publishing, setPublishing] = React.useState(false);
  const [publicToken, setPublicToken] = React.useState<string | null>(artifact.public_token);
  // 이전 버전 미리보기 — 선택 시 라이브 콘텐츠를 덮어쓴다.
  const [preview, setPreview] = React.useState<{ content: string; version: number } | null>(null);

  // 다른 아티팩트/버전으로 바뀌면 미리보기 초기화.
  React.useEffect(() => {
    setPreview(null);
    setPublicToken(artifact.public_token);
  }, [artifact.id, artifact.content, artifact.public_token]);

  const displayContent = preview?.content ?? artifact.content;
  const displayVersion = preview?.version ?? artifact.current_version;

  async function handleCopy() {
    await navigator.clipboard.writeText(displayContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleDownload() {
    const ext = TYPE_EXTENSIONS[artifact.artifact_type] ?? 'txt';
    const blob = new Blob([displayContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${artifact.identifier}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function handleShare() {
    setPublishing(true);
    try {
      const token = publicToken || (await artifactApi.publish(artifact.id));
      setPublicToken(token);
      await navigator.clipboard.writeText(`${window.location.origin}/artifact/${token}`);
      toast.success('공개 링크가 클립보드에 복사되었습니다.');
    } catch {
      toast.error('공유 링크 생성에 실패했습니다.');
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-md border border-border bg-card">
      <div className="flex flex-none items-center gap-2 border-b border-border bg-background px-3 py-2">
        <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
          {TYPE_LABELS[artifact.artifact_type] ?? artifact.artifact_type}
        </span>
        <span
          className="truncate text-sm font-medium"
          title={artifact.title || artifact.identifier}
        >
          {artifact.title || artifact.identifier}
        </span>

        <div className="ms-auto flex items-center gap-1">
          <VersionSwitcher
            artifactId={artifact.id}
            currentVersion={artifact.current_version}
            onSelectVersion={(content, version) => setPreview({ content, version })}
          />
          {onOpenChat && (
            <button
              type="button"
              onClick={onOpenChat}
              title="원본 대화 열기"
              className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <ExternalLink className="size-4" />
            </button>
          )}
          <button
            type="button"
            onClick={handleCopy}
            title="복사"
            className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            {copied ? <Check className="size-4 text-green-500" /> : <Copy className="size-4" />}
          </button>
          <button
            type="button"
            onClick={handleDownload}
            title="다운로드"
            className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <Download className="size-4" />
          </button>
          <button
            type="button"
            onClick={handleShare}
            disabled={publishing}
            title={publicToken ? '공개됨 — 링크 복사' : '공유'}
            className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-40"
          >
            <Share2 className="size-4" />
          </button>
          <button
            type="button"
            onClick={onClose}
            title="닫기"
            className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        </div>
      </div>

      {preview && (
        <div className="flex flex-none items-center justify-between bg-amber-500/10 px-3 py-1 text-xs text-amber-700 dark:text-amber-400">
          <span>이전 버전 v{displayVersion} 미리보기 중</span>
          <button type="button" className="underline" onClick={() => setPreview(null)}>
            최신 버전으로
          </button>
        </div>
      )}

      <div className="min-h-0 flex-1">
        <ArtifactRenderer
          type={artifact.artifact_type}
          content={displayContent}
          dataGet={() => artifactApi.getData(artifact.id)}
          dataSet={(data) => artifactApi.setData(artifact.id, data)}
        />
      </div>
    </div>
  );
}
