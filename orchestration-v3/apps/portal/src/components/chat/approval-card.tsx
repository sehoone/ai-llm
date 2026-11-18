'use client';

import { AlertTriangle, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useChatStore } from '@/stores/chat-store';

// HITL 승인 카드 (ADR-0008) — approval_required 시 도구 호출을 승인/거부.
export function ApprovalCard({ onDecision }: { onDecision: (approved: boolean) => void }) {
  const pending = useChatStore((s) => s.pendingApproval);
  const sending = useChatStore((s) => s.sending);
  if (!pending) return null;

  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-900/50 dark:bg-amber-950/30">
      <div className="mb-2 flex items-center gap-2 font-medium text-amber-700 dark:text-amber-400">
        <AlertTriangle className="size-4" /> 다음 작업에 승인이 필요합니다
      </div>
      <ul className="space-y-2">
        {pending.requests.map((r) => (
          <li key={r.tool_call_id} className="rounded-md border border-border bg-background p-2">
            <div className="font-mono text-xs font-medium">{r.name}</div>
            {r.reason && <div className="mt-0.5 text-xs text-muted-foreground">{r.reason}</div>}
            <pre className="mt-1 max-h-32 overflow-auto rounded bg-muted p-2 text-[11px] leading-relaxed">
              {JSON.stringify(r.args, null, 2)}
            </pre>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex justify-end gap-2">
        <Button variant="outline" size="sm" disabled={sending} onClick={() => onDecision(false)}>
          <X className="size-4" /> 거부
        </Button>
        <Button size="sm" disabled={sending} onClick={() => onDecision(true)}>
          <Check className="size-4" /> 승인
        </Button>
      </div>
    </div>
  );
}
