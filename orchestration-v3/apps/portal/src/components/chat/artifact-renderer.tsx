'use client';

import { Markdown } from '@/components/markdown';
import { SandboxFrame } from '@/components/artifacts/sandbox-frame';

type DataRecord = Record<string, unknown>;

// 샌드박스 iframe에서 실행/렌더하는 타입 (allow-scripts + CSP 잠금).
const SANDBOXED = new Set([
  'text/html',
  'application/vnd.react',
  'image/svg+xml',
  'application/vnd.mermaid',
]);

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
  dataGet,
  dataSet,
}: {
  type: string;
  content: string;
  complete?: boolean;
  dataGet?: () => Promise<DataRecord>;
  dataSet?: (data: DataRecord) => Promise<void>;
}) {
  if (type === 'text/markdown') {
    return (
      <div className="h-full overflow-auto p-4">
        <Markdown content={content} />
      </div>
    );
  }

  if (SANDBOXED.has(type)) {
    // 스트리밍 중에는 소스를 보여주고(부분 코드 실행 방지), 완료 후 샌드박스에서 실행.
    if (!complete) return <SourceView content={content} note="생성 중…" />;
    return <SandboxFrame type={type} content={content} dataGet={dataGet} dataSet={dataSet} />;
  }

  // application/vnd.code · 기타 → 실행하지 않고 소스 표시.
  return <SourceView content={content} />;
}
