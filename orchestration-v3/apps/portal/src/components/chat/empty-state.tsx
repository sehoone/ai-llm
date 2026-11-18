'use client';

const SUGGESTIONS = [
  { title: '문서 초안 작성', prompt: '다음 주제로 간단한 문서 초안을 작성해줘: ' },
  { title: '코드 설명', prompt: '아래 코드가 하는 일을 단계별로 설명해줘:\n\n' },
  { title: '내용 요약', prompt: '다음 내용을 핵심만 요약해줘:\n\n' },
  { title: '아이디어 브레인스토밍', prompt: '다음에 대한 아이디어를 10개 제안해줘: ' },
];

export function EmptyState({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center gap-8 px-4 py-16 text-center">
      <h1 className="text-2xl font-semibold">무엇을 도와드릴까요?</h1>
      <div className="grid w-full gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.title}
            onClick={() => onPick(s.prompt)}
            className="rounded-xl border border-border bg-card p-4 text-start text-sm transition hover:bg-accent hover:text-accent-foreground"
          >
            <div className="font-medium">{s.title}</div>
            <div className="mt-1 truncate text-xs text-muted-foreground">{s.prompt.trim()}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
