'use client';

import * as React from 'react';
import { artifactApi, type PublicArtifact } from '@/api/artifacts';
import { ArtifactRenderer } from '@/components/chat/artifact-renderer';

// 공개 아티팩트 뷰어 (ADR-0013) — 미인증. publish로 발급된 토큰으로 조회.
export default function PublicArtifactPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = React.use(params);
  const [art, setArt] = React.useState<PublicArtifact | null>(null);
  const [error, setError] = React.useState(false);

  React.useEffect(() => {
    artifactApi
      .getPublic(token)
      .then(setArt)
      .catch(() => setError(true));
  }, [token]);

  if (error) {
    return (
      <div className="flex min-h-svh items-center justify-center p-6 text-sm text-muted-foreground">
        공개된 아티팩트를 찾을 수 없습니다.
      </div>
    );
  }
  if (!art) {
    return (
      <div className="flex min-h-svh items-center justify-center p-6 text-sm text-muted-foreground">
        불러오는 중…
      </div>
    );
  }

  return (
    <div className="flex h-svh flex-col">
      <header className="border-b border-border px-4 py-3">
        <div className="text-sm font-medium">{art.title}</div>
        <div className="text-xs text-muted-foreground">
          {art.artifact_type} · v{art.version}
        </div>
      </header>
      <div className="min-h-0 flex-1">
        <ArtifactRenderer type={art.artifact_type} content={art.content} />
      </div>
    </div>
  );
}
