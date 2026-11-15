'use client';

import * as React from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Check, Copy } from 'lucide-react';

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

const COMPONENTS: Components = { pre: Pre };
const REMARK = [remarkGfm];
const REHYPE = [rehypeHighlight];

/**
 * 마크다운 렌더러. `content` 기준 memo — 스트리밍 중 동일 content면 재파싱하지 않는다.
 * (호출부에서 토큰 반영을 throttle해 과도한 재파싱을 줄인다.)
 */
export const Markdown = React.memo(function Markdown({ content }: { content: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={REMARK} rehypePlugins={REHYPE} components={COMPONENTS}>
        {content}
      </ReactMarkdown>
    </div>
  );
});
