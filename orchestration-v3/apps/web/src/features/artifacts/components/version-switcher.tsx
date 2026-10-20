'use client'

import { useEffect, useState } from 'react'

import { History } from 'lucide-react'

import { artifactService } from '@/api/artifacts'
import { logger } from '@/lib/logger'
import type { ArtifactVersionItem } from '@/types/chat-api'

interface VersionSwitcherProps {
  serverId?: string
  currentVersion: number
  /** Called when the user picks a version to preview. */
  onSelectVersion: (content: string, version: number) => void
}

export function VersionSwitcher({ serverId, currentVersion, onSelectVersion }: VersionSwitcherProps) {
  const [versions, setVersions] = useState<ArtifactVersionItem[]>([])
  const [selected, setSelected] = useState<number>(currentVersion)

  useEffect(() => {
    setSelected(currentVersion)
  }, [currentVersion])

  useEffect(() => {
    if (!serverId) {
      setVersions([])
      return
    }
    let cancelled = false
    artifactService
      .getVersions(serverId)
      .then((items) => {
        if (!cancelled) setVersions(items)
      })
      .catch((e) => logger.error('Failed to load artifact versions', e))
    return () => {
      cancelled = true
    }
  }, [serverId, currentVersion])

  // Only meaningful once there are at least two versions to switch between.
  if (!serverId || versions.length <= 1) return null

  const handleChange = async (version: number) => {
    setSelected(version)
    try {
      const v = await artifactService.getVersion(serverId, version)
      onSelectVersion(v.content, v.version)
    } catch (e) {
      logger.error('Failed to load artifact version', e)
    }
  }

  return (
    <label className='flex items-center gap-1.5 text-xs text-muted-foreground'>
      <History className='h-3.5 w-3.5' />
      <select
        className='rounded border border-border bg-background px-1.5 py-0.5 text-xs focus:outline-none'
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
  )
}
