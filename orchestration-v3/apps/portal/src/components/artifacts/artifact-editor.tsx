'use client';

import * as React from 'react';
import { toast } from 'sonner';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { artifactApi, type ArtifactDetail } from '@/api/artifacts';

const TYPES: { value: string; label: string }[] = [
  { value: 'text/html', label: 'HTML' },
  { value: 'application/vnd.react', label: 'React' },
  { value: 'image/svg+xml', label: 'SVG' },
  { value: 'application/vnd.mermaid', label: 'Mermaid' },
  { value: 'text/markdown', label: 'Markdown' },
  { value: 'application/vnd.code', label: 'Code' },
];

export function ArtifactEditor({
  onCreated,
  onCancel,
}: {
  onCreated: (detail: ArtifactDetail) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = React.useState('');
  const [type, setType] = React.useState('text/html');
  const [content, setContent] = React.useState('');
  const [saving, setSaving] = React.useState(false);

  async function create() {
    if (!content.trim()) {
      toast.error('내용을 입력하세요.');
      return;
    }
    setSaving(true);
    try {
      const detail = await artifactApi.create({
        title: title.trim() || '제목 없는 아티팩트',
        artifact_type: type,
        content,
      });
      toast.success('아티팩트를 만들었습니다.');
      onCreated(detail);
    } catch {
      toast.error('아티팩트 생성에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-md border border-border bg-card">
      <div className="flex flex-none items-center gap-2 border-b border-border bg-background px-3 py-2">
        <span className="text-sm font-medium">새 아티팩트</span>
        <button
          type="button"
          onClick={onCancel}
          title="닫기"
          className="ms-auto rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <X className="size-4" />
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4">
        <div className="flex gap-2">
          <Input
            placeholder="제목"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="flex-1"
          />
          <select
            className="rounded-md border border-border bg-background px-2 text-sm"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            {TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <Textarea
          placeholder="내용 (HTML·React·SVG·Mermaid·Markdown·코드)"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="min-h-0 flex-1 font-mono text-sm"
        />
        <div className="flex flex-none justify-end gap-2">
          <Button variant="outline" onClick={onCancel} disabled={saving}>
            취소
          </Button>
          <Button onClick={create} disabled={saving}>
            만들기
          </Button>
        </div>
      </div>
    </div>
  );
}
