'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight, FolderOpen, Layers, Plus, Pencil, Trash2, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'
import { ragGroupApi, type RagGroup, type RagKey } from '@/api/rag-groups'
import { logger } from '@/lib/logger'

interface GroupsTabProps {
  groups: RagGroup[]
  onRefresh: () => void
}

const COLOR_PRESETS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#ef4444',
  '#f97316', '#eab308', '#22c55e', '#14b8a6',
  '#3b82f6', '#64748b',
]

function CategoryFormDialog({
  open,
  onClose,
  initial,
  onSave,
}: {
  open: boolean
  onClose: () => void
  initial?: RagGroup
  onSave: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [color, setColor] = useState(initial?.color ?? '#6366f1')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      if (initial) {
        await ragGroupApi.updateGroup(initial.id, { name: name.trim(), description: description.trim() || undefined, color })
        toast.success('카테고리가 수정되었습니다')
      } else {
        await ragGroupApi.createGroup({ name: name.trim(), description: description.trim() || undefined, color })
        toast.success('카테고리가 생성되었습니다')
      }
      onSave()
      onClose()
    } catch (e) {
      logger.error(e)
      toast.error('저장에 실패했습니다')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className='max-w-md'>
        <DialogHeader>
          <DialogTitle>{initial ? '카테고리 수정' : '카테고리 생성'}</DialogTitle>
        </DialogHeader>
        <div className='flex flex-col gap-4 py-2'>
          <div className='flex flex-col gap-1.5'>
            <Label>이름 *</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder='카테고리 이름' />
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label>설명</Label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder='카테고리 설명 (선택)' rows={2} />
          </div>
          <div className='flex flex-col gap-2'>
            <Label>색상</Label>
            <div className='flex gap-2 flex-wrap'>
              {COLOR_PRESETS.map((c) => (
                <button
                  key={c}
                  className={`w-6 h-6 rounded-full border-2 transition-all ${color === c ? 'border-foreground scale-110' : 'border-transparent'}`}
                  style={{ backgroundColor: c }}
                  onClick={() => setColor(c)}
                />
              ))}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant='outline' onClick={onClose}>취소</Button>
          <Button onClick={handleSave} disabled={saving || !name.trim()}>저장</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function CategoryRow({ group, onRefresh }: { group: RagGroup; onRefresh: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [collections, setCollections] = useState<RagKey[]>([])
  const [loaded, setLoaded] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const loadCollections = async () => {
    if (loaded) return
    try {
      const data = await ragGroupApi.listGroupKeys(group.id)
      setCollections(data)
      setLoaded(true)
    } catch (e) {
      logger.error(e)
    }
  }

  const handleExpand = async () => {
    if (!expanded) await loadCollections()
    setExpanded((v) => !v)
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await ragGroupApi.deleteGroup(group.id)
      toast.success('카테고리가 삭제되었습니다')
      onRefresh()
    } catch (e) {
      logger.error(e)
      toast.error('삭제에 실패했습니다')
    } finally {
      setDeleting(false)
      setDeleteOpen(false)
    }
  }

  return (
    <>
      <div className='border rounded-lg overflow-hidden'>
        <div className='flex items-center gap-3 px-4 py-3 bg-muted/30 hover:bg-muted/50 transition-colors'>
          <button onClick={handleExpand} className='text-muted-foreground hover:text-foreground'>
            {expanded ? <ChevronDown className='h-4 w-4' /> : <ChevronRight className='h-4 w-4' />}
          </button>
          <div className='w-3 h-3 rounded-full shrink-0' style={{ backgroundColor: group.color }} />
          <FolderOpen className='h-4 w-4 text-muted-foreground shrink-0' />
          <div className='flex-1 min-w-0'>
            <div className='font-medium text-sm'>{group.name}</div>
            {group.description && <div className='text-xs text-muted-foreground truncate'>{group.description}</div>}
          </div>
          <div className='flex gap-2 shrink-0'>
            <Badge variant='secondary' className='text-xs gap-1'>
              <Layers className='h-3 w-3' />{group.key_count} 컬렉션
            </Badge>
            <Badge variant='secondary' className='text-xs gap-1'>
              <FileText className='h-3 w-3' />{group.doc_count} 문서
            </Badge>
          </div>
          <div className='flex gap-1 shrink-0'>
            <Button size='icon' variant='ghost' className='h-7 w-7' onClick={() => setEditOpen(true)}>
              <Pencil className='h-3.5 w-3.5' />
            </Button>
            <Button size='icon' variant='ghost' className='h-7 w-7 text-destructive hover:text-destructive' onClick={() => setDeleteOpen(true)}>
              <Trash2 className='h-3.5 w-3.5' />
            </Button>
          </div>
        </div>

        {expanded && (
          <div className='border-t divide-y'>
            {collections.length === 0 ? (
              <div className='px-8 py-3 text-sm text-muted-foreground'>컬렉션이 없습니다</div>
            ) : (
              collections.map((col) => (
                <div key={col.id} className='flex items-center gap-3 px-8 py-2.5'>
                  <Layers className='h-3.5 w-3.5 text-muted-foreground shrink-0' />
                  <div className='flex-1 min-w-0'>
                    <div className='text-sm font-mono'>{col.rag_key}</div>
                    {col.description && <div className='text-xs text-muted-foreground'>{col.description}</div>}
                  </div>
                  <Badge variant='outline' className='text-xs'>{col.rag_type}</Badge>
                  <Badge variant='secondary' className='text-xs gap-1'>
                    <FileText className='h-3 w-3' />{col.doc_count}
                  </Badge>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <CategoryFormDialog
        open={editOpen}
        onClose={() => setEditOpen(false)}
        initial={group}
        onSave={onRefresh}
      />

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>카테고리 삭제</AlertDialogTitle>
            <AlertDialogDescription>
              <strong>{group.name}</strong> 카테고리를 삭제합니다. 하위 컬렉션 설정이 함께 삭제되며 문서는 보존됩니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={deleting} className='bg-destructive text-destructive-foreground hover:bg-destructive/90'>
              삭제
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

export function GroupsTab({ groups, onRefresh }: GroupsTabProps) {
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <div className='flex flex-col gap-4'>
      <div className='flex items-center justify-between'>
        <p className='text-sm text-muted-foreground'>
          {groups.length}개 카테고리 · 총 {groups.reduce((s, g) => s + g.doc_count, 0)}개 문서
        </p>
        <Button size='sm' onClick={() => setCreateOpen(true)}>
          <Plus className='h-4 w-4 mr-1' />카테고리 추가
        </Button>
      </div>

      {groups.length === 0 ? (
        <div className='rounded-lg border border-dashed p-10 text-center text-muted-foreground text-sm'>
          카테고리가 없습니다. 카테고리를 추가하여 컬렉션을 구조화하세요.
        </div>
      ) : (
        <div className='flex flex-col gap-2'>
          {groups.map((g) => (
            <CategoryRow key={g.id} group={g} onRefresh={onRefresh} />
          ))}
        </div>
      )}

      <CategoryFormDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSave={onRefresh}
      />
    </div>
  )
}
