'use client';

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { ArrowLeft, FileText, MessageSquarePlus, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { projectsApi, type Project, type ProjectKnowledge, type ProjectSession } from '@/api/projects';
import { skillsApi, type Skill } from '@/api/skills';
import { useChat } from '@/hooks/use-chat';
import { useChatStore } from '@/stores/chat-store';

export default function ProjectDetailPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const { selectSession, newChat } = useChat();
  const setActiveProjectId = useChatStore((s) => s.setActiveProjectId);

  const [project, setProject] = React.useState<Project | null>(null);
  const [sessions, setSessions] = React.useState<ProjectSession[]>([]);
  const [knowledge, setKnowledge] = React.useState<ProjectKnowledge[]>([]);
  const [allSkills, setAllSkills] = React.useState<Skill[]>([]);
  const [skillIds, setSkillIds] = React.useState<string[]>([]);
  const [instructions, setInstructions] = React.useState('');
  const [savingInstr, setSavingInstr] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const fileRef = React.useRef<HTMLInputElement>(null);

  const load = React.useCallback(async () => {
    try {
      const [p, ss, ks, sk, allSk] = await Promise.all([
        projectsApi.get(id),
        projectsApi.listSessions(id),
        projectsApi.listKnowledge(id),
        projectsApi.listSkills(id),
        skillsApi.list(),
      ]);
      setProject(p);
      setInstructions(p.instructions);
      setSessions(ss);
      setKnowledge(ks);
      setSkillIds(sk);
      setAllSkills(allSk);
    } catch {
      toast.error('프로젝트를 불러오지 못했습니다.');
    }
  }, [id]);
  React.useEffect(() => {
    load();
  }, [load]);

  async function saveInstructions() {
    setSavingInstr(true);
    try {
      await projectsApi.update(id, { instructions });
      toast.success('지침을 저장했습니다.');
    } catch {
      toast.error('지침 저장에 실패했습니다.');
    } finally {
      setSavingInstr(false);
    }
  }

  async function onUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      for (const f of Array.from(files)) {
        const content = await f.text();
        const doc = await projectsApi.addKnowledge(id, f.name, content);
        setKnowledge((prev) => [...prev, doc]);
      }
      toast.success('지식을 추가했습니다.');
    } catch {
      toast.error('지식 추가에 실패했습니다. (텍스트 파일만 지원)');
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  async function removeKnowledge(docId: number) {
    try {
      await projectsApi.deleteKnowledge(id, docId);
      setKnowledge((prev) => prev.filter((k) => k.id !== docId));
    } catch {
      toast.error('삭제하지 못했습니다.');
    }
  }

  // 기본 활성 스킬 토글 (ADR-0024 §4) — 낙관적 반영 후 전체 교체 저장. 실패 시 롤백.
  async function toggleSkill(sid: string) {
    const next = skillIds.includes(sid)
      ? skillIds.filter((x) => x !== sid)
      : [...skillIds, sid];
    const prev = skillIds;
    setSkillIds(next);
    try {
      setSkillIds(await projectsApi.setSkills(id, next));
    } catch {
      setSkillIds(prev);
      toast.error('기본 스킬을 저장하지 못했습니다.');
    }
  }

  function startNewChat() {
    setActiveProjectId(id);
    newChat();
    router.push('/chat');
  }

  function openSession(sessionId: number) {
    setActiveProjectId(id);
    selectSession(sessionId);
    router.push('/chat');
  }

  if (!project) {
    return <div className="p-6 text-sm text-muted-foreground">불러오는 중…</div>;
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-5xl p-6">
        <button
          onClick={() => router.push('/projects')}
          className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> 프로젝트 목록
        </button>
        <header className="mb-6">
          <h1 className="text-xl font-semibold" style={{ color: project.color }}>
            {project.name}
          </h1>
          {project.description && (
            <p className="mt-1 text-sm text-muted-foreground">{project.description}</p>
          )}
        </header>

        <div className="grid gap-6 md:grid-cols-[1fr_320px]">
          {/* 좌: 대화 */}
          <section>
            <Button onClick={startNewChat} className="mb-4 w-full justify-start">
              <MessageSquarePlus /> 이 프로젝트에서 새 대화
            </Button>
            <h2 className="mb-2 text-sm font-medium text-muted-foreground">이 프로젝트의 대화</h2>
            <div className="space-y-1">
              {sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => openSession(s.id)}
                  className="flex w-full items-center rounded-md px-3 py-2 text-start text-sm hover:bg-accent hover:text-accent-foreground"
                >
                  <span className="truncate">{s.title || '새 대화'}</span>
                </button>
              ))}
              {sessions.length === 0 && (
                <p className="px-3 py-2 text-xs text-muted-foreground">아직 대화가 없습니다.</p>
              )}
            </div>
          </section>

          {/* 우: 지식 + 지침 */}
          <aside className="space-y-6">
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="mb-3 flex items-center gap-2">
                <h2 className="flex-1 text-sm font-medium">프로젝트 지식</h2>
                <input
                  ref={fileRef}
                  type="file"
                  multiple
                  accept=".txt,.md,.csv,.json,text/*"
                  className="hidden"
                  onChange={(e) => onUpload(e.target.files)}
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading}
                >
                  <Plus className="size-4" /> 콘텐츠 추가
                </Button>
              </div>
              <div className="space-y-1">
                {knowledge.map((k) => (
                  <div
                    key={k.id}
                    className="group/doc flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent/50"
                  >
                    <FileText className="size-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 truncate" title={k.filename}>
                      {k.filename}
                    </span>
                    <button
                      onClick={() => removeKnowledge(k.id)}
                      className="text-muted-foreground opacity-0 transition hover:text-destructive group-hover/doc:opacity-100"
                      aria-label="삭제"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                ))}
                {knowledge.length === 0 && (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground">
                    텍스트 파일을 추가하면 이 프로젝트 대화에서 자동 검색됩니다.
                  </p>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card p-4">
              <h2 className="text-sm font-medium">기본 활성 스킬</h2>
              <p className="mb-3 mt-0.5 text-xs text-muted-foreground">
                이 프로젝트의 대화에 자동 적용됩니다.
              </p>
              <div className="space-y-1">
                {allSkills.map((s) => {
                  const on = skillIds.includes(s.id);
                  return (
                    <button
                      key={s.id}
                      onClick={() => toggleSkill(s.id)}
                      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-start text-sm hover:bg-accent/50"
                    >
                      <span
                        className={`size-3.5 shrink-0 rounded-sm border ${
                          on ? 'border-indigo-500 bg-indigo-500' : 'border-input'
                        }`}
                      />
                      <span className="min-w-0 flex-1 truncate" style={on ? { color: s.color } : undefined}>
                        {s.name}
                      </span>
                    </button>
                  );
                })}
                {allSkills.length === 0 && (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground">
                    먼저 스킬을 만들어주세요. (설정 → 스킬)
                  </p>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card p-4">
              <h2 className="mb-2 text-sm font-medium">프로젝트 지침</h2>
              <Textarea
                rows={6}
                placeholder="이 프로젝트의 모든 대화에 적용될 system prompt."
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
              />
              <div className="mt-2 flex justify-end">
                <Button size="sm" onClick={saveInstructions} disabled={savingInstr}>
                  저장
                </Button>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
