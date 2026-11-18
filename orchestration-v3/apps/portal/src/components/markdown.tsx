'use client';

import * as React from 'react';
import ReactMarkdown, { type Components, defaultUrlTransform } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Check, Copy } from 'lucide-react';
import { useArtifactStore } from '@/stores/artifact-store';

/** 링크 — `artifact:<id>`(아티팩트 칩)는 패널을 여는 버튼, 그 외는 새 탭 링크. */
function Anchor({
  href,
  children,
  node,
  ...props
}: React.ComponentProps<'a'> & { node?: unknown }) {
  void node;
  if (href && href.startsWith('artifact:')) {
    const id = href.slice('artifact:'.length);
    return (
      <button
        type="button"
        onClick={() => useArtifactStore.getState().openPanel(id)}
        className="my-1 inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1 text-sm font-medium no-underline transition hover:bg-accent"
      >
        {children}
      </button>
    );
  }
  return (
    <a href={href} target="_blank" rel="noreferrer" {...props}>
      {children}
    </a>
  );
}

/** 코드블록 — 우상단 복사 버튼. 텍스트는 렌더된 <pre>.innerText에서 추출. */
function Pre({ children, node, ...props }: React.ComponentProps<'pre'> & { node?: unknown }) {
  void node; // react-markdown이 주입하는 node를 DOM으로 흘리지 않음
  const ref = React.useRef<HTMLPreElement>(null);
  const [copied, setCopied] = React.useState(false);

  async function copy() {
    const text = ref.current?.innerText ?? '';
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* 클립보드 권한 없음 — 무시 */
    }
  }

  return (
    <div className="group relative">
      <button
        type="button"
        onClick={copy}
        aria-label="코드 복사"
        className="absolute end-2 top-2 rounded-md bg-white/10 p-1.5 text-white/70 opacity-0 transition hover:bg-white/20 hover:text-white group-hover:opacity-100"
      >
        {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
      </button>
      <pre ref={ref} {...props}>
        {children}
      </pre>
    </div>
  );
}

const COMPONENTS: Components = { pre: Pre, a: Anchor };
const REMARK = [remarkGfm];
const REHYPE = [rehypeHighlight];

// 기본 sanitize가 `artifact:` 커스텀 프로토콜(아티팩트 칩)을 지우므로 통과시킨다.
function urlTransform(url: string): string {
  return url.startsWith('artifact:') ? url : defaultUrlTransform(url);
}

/**
 * 마크다운 렌더러. `content` 기준 memo — 스트리밍 중 동일 content면 재파싱하지 않는다.
 * (호출부에서 토큰 반영을 throttle해 과도한 재파싱을 줄인다.)
 */
export const Markdown = React.memo(function Markdown({ content }: { content: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={REMARK}
        rehypePlugins={REHYPE}
        components={COMPONENTS}
        urlTransform={urlTransform}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
