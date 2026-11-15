'use client';

import * as React from 'react';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { ChatSidebar } from '@/components/chat/chat-sidebar';
import { ChatMessages } from '@/components/chat/chat-messages';
import { Composer } from '@/components/chat/composer';
import { useChat } from '@/hooks/use-chat';

export default function ChatPage() {
  const { loadSessions, selectSession, newChat, send, regenerate, stop, rename, remove } = useChat();
  const [draft, setDraft] = React.useState('');
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  function handleSubmit() {
    const t = draft.trim();
    if (!t) return;
    setDraft('');
    void send(t);
  }

  function pickPrompt(p: string) {
    setDraft(p);
    textareaRef.current?.focus();
  }

  const renderSidebar = (onNavigate?: () => void) => (
    <ChatSidebar
      onSelect={selectSession}
      onNewChat={newChat}
      onRename={rename}
      onRemove={remove}
      onNavigate={onNavigate}
    />
  );

  return (
    <div className="flex h-svh">
      <aside className="hidden w-72 shrink-0 border-e border-sidebar-border md:block">
        {renderSidebar()}
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-border p-2 md:hidden">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="대화 목록 열기">
                <Menu />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-72 p-0">
              <SheetTitle className="sr-only">대화 목록</SheetTitle>
              {renderSidebar(() => setMobileOpen(false))}
            </SheetContent>
          </Sheet>
          <span className="text-sm font-medium">AI 포털</span>
        </header>

        <ChatMessages onRegenerate={regenerate} onPickPrompt={pickPrompt} />
        <Composer
          value={draft}
          onChange={setDraft}
          onSubmit={handleSubmit}
          onStop={stop}
          textareaRef={textareaRef}
        />
      </main>
    </div>
  );
}
