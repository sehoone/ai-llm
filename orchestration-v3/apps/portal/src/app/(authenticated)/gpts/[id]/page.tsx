'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { ArrowLeft, ArrowUp, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Markdown } from '@/components/markdown';
import { gptsApi, streamGptChat, type CustomGpt, type GptMessage } from '@/api/gpts';

export default function GptChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const router = useRouter();
  const [gpt, setGpt] = React.useState<CustomGpt | null>(null);
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [messages, setMessages] = React.useState<GptMessage[]>([]);
  const [input, setInput] = React.useState('');
  const [sending, setSending] = React.useState(false);
  const abortRef = React.useRef<AbortController | null>(null);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    (async () => {
      try {
        const [g, s] = await Promise.all([gptsApi.get(id), gptsApi.createSession(id)]);
        setGpt(g);
        setSessionId(s.session_id);
      } catch {
        toast.error('GPT를 불러오지 못했습니다.');
      }
    })();
  }, [id]);

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || sending || !sessionId) return;
    setInput('');
    setSending(true);
    const next: GptMessage[] = [...messages, { role: 'user', content: text }];
    setMessages([...next, { role: 'assistant', content: '' }]);
    const controller = new AbortController();
    abortRef.current = controller;
    await streamGptChat(
      id,
      { session_id: sessionId, messages: next },
      {
        onContent: (t) =>
          setMessages((prev) => {
            const n = [...prev];
            n[n.length - 1] = { ...n[n.length - 1], content: n[n.length - 1].content + t };
            return n;
          }),
        onError: (d) => toast.error(d),
      },
      controller.signal
    );
    setSending(false);
    abortRef.current = null;
  }

  function stop() {
    abortRef.current?.abort();
    setSending(false);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  const lastIndex = messages.length - 1;

  return (
    <div className="flex h-svh flex-col">
      <header className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Button variant="ghost" size="icon" onClick={() => router.push('/gpts')} aria-label="뒤로">
          <ArrowLeft />
        </Button>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{gpt?.name ?? 'GPT'}</div>
          {gpt?.description && (
            <div className="truncate text-xs text-muted-foreground">{gpt.description}</div>
          )}
        </div>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-5 px-4 py-6">
          {messages.length === 0 && (
            <p className="pt-20 text-center text-sm text-muted-foreground">
              이 GPT와 대화를 시작하세요.
            </p>
          )}
          {messages.map((m, i) =>
            m.role === 'user' ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl bg-primary px-4 py-2 text-sm whitespace-pre-wrap text-primary-foreground">
                  {m.content}
                </div>
              </div>
            ) : (
              <div key={i} className="flex justify-start">
                <div className="w-full max-w-[80%]">
                  {m.content ? (
                    <Markdown content={m.content} />
                  ) : sending && i === lastIndex ? (
                    <span className="text-muted-foreground">…</span>
                  ) : null}
                </div>
              </div>
            )
          )}
        </div>
      </div>

      <div className="border-t border-border bg-background p-4">
        <div className="mx-auto flex max-w-3xl items-end gap-1 rounded-2xl border border-input bg-card p-1">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="메시지를 입력하세요 (Enter 전송)"
            className="max-h-40 resize-none border-0 bg-transparent py-2 shadow-none focus-visible:ring-0"
          />
          <Button
            size="icon"
            className="size-9 shrink-0 rounded-full"
            onClick={sending ? stop : send}
            disabled={!sending && !input.trim()}
            aria-label={sending ? '중단' : '전송'}
          >
            {sending ? <Square className="size-4" /> : <ArrowUp className="size-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
