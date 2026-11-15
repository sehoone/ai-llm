'use client';

import * as React from 'react';
import { Check, Copy, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function MessageActions({
  content,
  onRegenerate,
}: {
  content: string;
  onRegenerate?: () => void;
}) {
  const [copied, setCopied] = React.useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* 무시 */
    }
  }

  return (
    <div className="mt-1 flex items-center gap-1 text-muted-foreground opacity-0 transition group-hover/msg:opacity-100">
      <Button variant="ghost" size="icon" className="size-7" onClick={copy} aria-label="복사">
        {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
      </Button>
      {onRegenerate && (
        <Button
          variant="ghost"
          size="icon"
          className="size-7"
          onClick={onRegenerate}
          aria-label="다시 생성"
        >
          <RefreshCw className="size-3.5" />
        </Button>
      )}
    </div>
  );
}
