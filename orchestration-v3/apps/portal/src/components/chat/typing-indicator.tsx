export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1" aria-label="응답 생성 중">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="size-2 animate-bounce rounded-full bg-muted-foreground/50"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
}
