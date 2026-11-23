'use client';

import * as React from 'react';
import { History } from 'lucide-react';
import { artifactApi, type ArtifactVersionItem } from '@/api/artifacts';
import { logger } from '@/lib/logger';

interface VersionSwitcherProps {
  artifactId: string;
  currentVersion: number;
  /** 사용자가 미리볼 버전을 고르면 호출. */
  onSelectVersion: (content: string, version: number) => void;
}

export function VersionSwitcher({ artifactId, currentVersion, onSelectVersion }: VersionSwitcherProps) {
  const [versions, setVersions] = React.useState<ArtifactVersionItem[]>([]);
  const [selected, setSelected] = React.useState<number>(currentVersion);

  React.useEffect(() => {
    setSelected(currentVersion);
  }, [currentVersion]);

  React.useEffect(() => {
    let cancelled = false;
    artifactApi
      .getVersions(artifactId)
      .then((items) => {
        if (!cancelled) setVersions(items);
      })
      .catch((e) => logger.error('Failed to load artifact versions', e));
    return () => {
      cancelled = true;
    };
  }, [artifactId, currentVersion]);

  // 버전이 2개 이상일 때만 의미가 있다.
  if (versions.length <= 1) return null;

  async function handleChange(version: number) {
    setSelected(version);
    try {
      const v = await artifactApi.getVersion(artifactId, version);
      onSelectVersion(v.content, v.version);
    } catch (e) {
      logger.error('Failed to load artifact version', e);
    }
  }

  return (
    <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <History className="size-3.5" />
      <select
        className="rounded border border-border bg-background px-1.5 py-0.5 text-xs focus:outline-none"
        value={selected}
        onChange={(e) => handleChange(Number(e.target.value))}
      >
        {versions.map((v) => (
          <option key={v.version} value={v.version}>
            v{v.version}
            {v.version === currentVersion ? ' (최신)' : ''}
          </option>
        ))}
      </select>
    </label>
  );
}
