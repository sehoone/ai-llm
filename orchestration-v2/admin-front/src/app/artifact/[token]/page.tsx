'use client'

import { useEffect, useState } from 'react'

import { useParams } from 'next/navigation'

import { Loader2 } from 'lucide-react'

import { logger } from '@/lib/logger'
import { ArtifactRenderer } from '@/features/artifacts/components/artifact-renderer'

interface PublicArtifact {
  title: string
  artifact_type: string
  content: string
  version: number
}

/**
 * Public, unauthenticated view of a published artifact. Lives outside the
 * `(authenticated)` route group, so no login is required. Fetches with a plain
 * `fetch` to bypass the authenticated axios instance.
 */
export default function PublicArtifactPage() {
  const params = useParams<{ token: string }>()
  const token = params?.token

  const [artifact, setArtifact] = useState<PublicArtifact | null>(null)
  const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')

  useEffect(() => {
    if (!token) return
    const base = process.env.NEXT_PUBLIC_API_URL || ''
    fetch(`${base}/api/v1/public/artifacts/${token}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: PublicArtifact) => {
        setArtifact(data)
        setStatus('ready')
      })
      .catch((e) => {
        logger.error('Failed to load public artifact', e)
        setStatus('error')
      })
  }, [token])

  if (status === 'loading') {
    return (
      <div className='flex h-screen items-center justify-center'>
        <Loader2 className='h-6 w-6 animate-spin text-muted-foreground' />
      </div>
    )
  }

  if (status === 'error' || !artifact) {
    return (
      <div className='flex h-screen flex-col items-center justify-center gap-2 text-center'>
        <h1 className='text-lg font-semibold'>아티펙트를 찾을 수 없습니다</h1>
        <p className='text-sm text-muted-foreground'>링크가 만료되었거나 비공개로 전환되었을 수 있습니다.</p>
      </div>
    )
  }

  return (
    <div className='flex h-screen flex-col'>
      <header className='flex flex-none items-center gap-2 border-b bg-background px-4 py-3'>
        <span className='truncate text-sm font-medium'>{artifact.title || 'Artifact'}</span>
        <span className='text-xs text-muted-foreground'>v{artifact.version}</span>
      </header>
      <main className='min-h-0 flex-1'>
        <ArtifactRenderer
          type={artifact.artifact_type}
          content={artifact.content}
          dataGet={async () => {
            const base = process.env.NEXT_PUBLIC_API_URL || ''
            const res = await fetch(`${base}/api/v1/public/artifacts/${token}/data`)
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            return (await res.json()).data as Record<string, unknown>
          }}
          dataSet={async (data) => {
            const base = process.env.NEXT_PUBLIC_API_URL || ''
            const res = await fetch(`${base}/api/v1/public/artifacts/${token}/data`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ data }),
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
          }}
        />
      </main>
    </div>
  )
}
