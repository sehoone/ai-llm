'use client';

import { Markdown } from '@/components/markdown';

// 정적 렌더(샌드박스 iframe, 스크립트 불가 — 안전한 미리보기). react·mermaid 등 JS 필요 타입은 소스 표시.
const SANDBOXED = new Set(['text/html', 'image/svg+xml']);

function SourceView({ content, note }: { content: string; note?: string }) {
  return (
    <div className="h-full overflow-auto bg-[#0d1117] p-4">
      {note && <div className="mb-2 text-xs text-zinc-400">{note}</div>}
      <pre className="overflow-x-auto">
        <code className="font-mono text-sm leading-relaxed text-zinc-100">{content}</code>
      </pre>
    </div>
  );
}

export function ArtifactRenderer({
  type,
  content,
  complete = true,
}: {
  type: string;
  content: string;
  complete?: boolean;
}) {
  if (type === 'text/markdown') {
    return (
      <div className="h-full overflow-auto p-4">
        <Markdown content={content} />
      </div>
    );
  }

  if (SANDBOXED.has(type)) {
    // 스트리밍 중에는 소스를 라이브로 보여주고(재로드 폭주 방지), 완료 후 iframe을 1회 마운트.
    if (!complete) return <SourceView content={content} note="생성 중…" />;
    return (
      <iframe
        // sandbox="" → 스크립트·폼·동일출처 전부 차단, HTML/CSS/SVG만 정적 렌더.
        key={content.length}
        sandbox=""
        srcDoc={content}
        title="artifact"
        className="h-full w-full border-0 bg-white"
      />
    );
  }

  // application/vnd.code · mermaid · react · unknown → 실행하지 않고 소스 표시.
  return <SourceView content={content} />;
}
