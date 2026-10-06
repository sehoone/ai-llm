'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import { useRouter } from 'next/navigation'

import { ExternalLink, Search as SearchIcon, Shapes } from 'lucide-react'
import { toast } from 'sonner'

import { artifactService } from '@/api/artifacts'
import { chatService } from '@/api/chat'
import { logger } from '@/lib/logger'
import { useArtifactStore } from '@/stores/artifact-store'
import type { ArtifactSummary } from '@/types/chat-api'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { ThemeSwitch } from '@/components/theme-switch'

import { ArtifactCard } from './components/artifact-card'
import { ArtifactPanel } from './components/artifact-panel'

const TYPE_FILTERS: { value: string; label: string }[] = [
  { value: 'all', label: '전체 타입' },
  { value: 'text/html', label: 'HTML' },
  { value: 'application/vnd.react', label: 'React' },
  { value: 'image/svg+xml', label: 'SVG' },
  { value: 'application/vnd.mermaid', label: 'Mermaid' },
  { value: 'text/markdown', label: 'Markdown' },
  { value: 'application/vnd.code', label: 'Code' },
]

export function Artifacts() {
  const router = useRouter()
  const { open, setActive, upsertArtifact, reset } = useArtifactStore()
  const isOpen = useArtifactStore((s) => s.isOpen)

  const [artifacts, setArtifacts] = useState<ArtifactSummary[]>([])
  const [sessionNames, setSessionNames] = useState<Record<string, string>>({})
  const [selected, setSelected] = useState<ArtifactSummary | null>(null)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [publishedOnly, setPublishedOnly] = useState(false)
  const [toDelete, setToDelete] = useState<ArtifactSummary | null>(null)

  const loadList = useCallback(async () => {
    try {
      const items = await artifactService.list()
      setArtifacts(items)
    } catch (error) {
      logger.error('Failed to load artifacts', error)
      toast.error('아티펙트 목록을 불러오지 못했습니다')
    }
  }, [])

  useEffect(() => {
    // Clear any artifact state carried over from the chat canvas.
    reset()
    loadList()
    chatService
      .getSessions()
      .then((sessions) => {
        const map: Record<string, string> = {}
        for (const s of sessions) map[s.session_id] = s.name || 'New Chat'
        setSessionNames(map)
      })
      .catch((error) => logger.error('Failed to load sessions', error))
  }, [loadList, reset])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return artifacts.filter((a) => {
      if (typeFilter !== 'all' && a.artifact_type !== typeFilter) return false
      if (publishedOnly && !a.is_published) return false
      if (q && !(a.title || a.identifier).toLowerCase().includes(q)) return false
      return true
    })
  }, [artifacts, search, typeFilter, publishedOnly])

  const handleSelect = useCallback(
    async (summary: ArtifactSummary) => {
      setSelected(summary)
      try {
        const detail = await artifactService.get(summary.id)
        upsertArtifact({
          identifier: detail.identifier,
          type: detail.artifact_type,
          title: detail.title,
          content: detail.content,
          version: detail.current_version,
          isStreaming: false,
          serverId: detail.id,
        })
        setActive(detail.identifier)
        open(detail.identifier)
      } catch (error) {
        logger.error('Failed to load artifact', error)
        toast.error('아티펙트를 불러오지 못했습니다')
      }
    },
    [open, setActive, upsertArtifact]
  )

  const handleDelete = useCallback(async () => {
    if (!toDelete) return
    try {
      await artifactService.remove(toDelete.id)
      setArtifacts((prev) => prev.filter((a) => a.id !== toDelete.id))
      if (selected?.id === toDelete.id) {
        setSelected(null)
        useArtifactStore.getState().close()
      }
      toast.success('아티펙트를 삭제했습니다')
    } catch (error) {
      logger.error('Failed to delete artifact', error)
      toast.error('삭제에 실패했습니다')
    } finally {
      setToDelete(null)
    }
  }, [toDelete, selected])

  return (
    <>
      <Header>
        <div className='flex items-center gap-2'>
          <Shapes size={20} />
          <h1 className='text-lg font-semibold'>Artifacts</h1>
        </div>
        <div className='ms-auto flex items-center space-x-4'>
          <ThemeSwitch />
          <ProfileDropdown />
        </div>
      </Header>

      <Main fixed>
        <section className='flex h-full gap-4'>
          {/* Left — library list */}
          <div className='flex w-full flex-col gap-3 sm:w-72 lg:w-80'>
            <label className='flex h-10 items-center rounded-md border border-border ps-2'>
              <SearchIcon size={15} className='me-2 stroke-slate-500' />
              <input
                type='text'
                className='w-full flex-1 bg-inherit text-sm focus-visible:outline-hidden'
                placeholder='아티펙트 검색...'
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>

            <div className='flex items-center gap-2'>
              <select
                className='flex-1 rounded-md border border-border bg-background px-2 py-1.5 text-xs'
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                {TYPE_FILTERS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
              <label className='flex items-center gap-1 text-xs text-muted-foreground'>
                <input
                  type='checkbox'
                  checked={publishedOnly}
                  onChange={(e) => setPublishedOnly(e.target.checked)}
                />
                공개됨
              </label>
            </div>

            <div className='flex-1 space-y-2 overflow-y-auto pe-1'>
              {filtered.map((a) => (
                <ArtifactCard
                  key={a.id}
                  artifact={a}
                  sessionName={sessionNames[a.session_id]}
                  selected={selected?.id === a.id}
                  onClick={() => handleSelect(a)}
                  onDelete={() => setToDelete(a)}
                />
              ))}
              {filtered.length === 0 && (
                <div className='py-8 text-center text-sm text-muted-foreground'>
                  아티펙트가 없습니다
                </div>
              )}
            </div>
          </div>

          {/* Right — preview */}
          <div className='hidden min-w-0 flex-1 flex-col md:flex'>
            {isOpen && selected ? (
              <div className='flex h-full flex-col gap-2'>
                <div className='flex flex-none items-center justify-end'>
                  <Button
                    variant='outline'
                    size='sm'
                    onClick={() => router.push(`/chats?session=${selected.session_id}`)}
                  >
                    <ExternalLink className='me-1 h-3.5 w-3.5' />
                    원본 대화 열기
                  </Button>
                </div>
                <div className='min-h-0 flex-1'>
                  <ArtifactPanel />
                </div>
              </div>
            ) : (
              <div className='flex h-full flex-col items-center justify-center gap-3 rounded-md border border-dashed text-muted-foreground'>
                <Shapes className='h-10 w-10' />
                <p className='text-sm'>왼쪽에서 아티펙트를 선택하세요</p>
              </div>
            )}
          </div>
        </section>

        <Dialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>아티펙트 삭제</DialogTitle>
              <DialogDescription>
                &lsquo;{toDelete?.title || toDelete?.identifier}&rsquo; 아티펙트와 모든 버전을 삭제합니다. 되돌릴 수 없습니다.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant='outline' onClick={() => setToDelete(null)}>
                취소
              </Button>
              <Button variant='destructive' onClick={handleDelete}>
                삭제
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Main>
    </>
  )
}
