'use client'

import { useState } from 'react'
import {
  ChevronDown, ChevronRight, FolderOpen, Layers,
  Plus, Pencil, Trash2, Database,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'
import { ragGroupApi, type RagGroup, type RagKey } from '@/api/rag-groups'
import { logger } from '@/lib/logger'

export type SelectedNode =
  | { type: 'all' }
  | { type: 'group'; groupName: string }
  | { type: 'index'; groupName: string; indexKey: string }

interface TreePanelProps {
  groups: RagGroup[]
  keys: RagKey[]
  selected: SelectedNode
  onSelect: (node: SelectedNode) => void
  onRefresh: () => void
}

const COLOR_PRESETS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#ef4444',
  '#f97316', '#eab308', '#22c55e', '#14b8a6',
  '#3b82f6', '#64748b',
]

function GroupFormDialog({ open, onClose, initial, onSave }: {
  open: boolean; onClose: () => void; initial?: RagGroup; onSave: () => void
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
        toast.success('그룹이 수정되었습니다')
      } else {
        await ragGroupApi.createGroup({ name: name.trim(), description: description.trim() || undefined, color })
        toast.success('그룹이 생성되었습니다')
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
          <DialogTitle>{initial ? '그룹 수정' : '그룹 생성'}</DialogTitle>
        </DialogHeader>
        <div className='flex flex-col gap-4 py-2'>
          <div className='flex flex-col gap-1.5'>
            <Label>이름 *</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder='그룹 이름' />
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label>설명</Label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder='그룹 설명 (선택)' rows={2} />
          </div>
          <div className='flex flex-col gap-2'>
            <Label>색상</Label>
            <div className='flex gap-2 flex-wrap'>
              {COLOR_PRESETS.map((c) => (
                <button
                  key={c}
                  type='button'
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

function IndexFormDialog({ open, onClose, initial, groups, defaultGroup, onSave }: {
  open: boolean; onClose: () => void; initial?: RagKey
  groups: RagGroup[]; defaultGroup?: string; onSave: () => void
}) {
  const [ragKey, setRagKey] = useState(initial?.rag_key ?? '')
  const [ragGroup, setRagGroup] = useState(initial?.rag_group ?? defaultGroup ?? (groups[0]?.name ?? ''))
  const [description, setDescription] = useState(initial?.description ?? '')
  const [ragType, setRagType] = useState(initial?.rag_type ?? 'chatbot_shared')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!ragKey.trim() || !ragGroup.trim()) return
    setSaving(true)
    try {
      if (initial) {
        await ragGroupApi.updateKey(initial.id, {
          rag_group: ragGroup.trim(),
          description: description.trim() || undefined,
          rag_type: ragType,
        })
        toast.success('인덱스가 수정되었습니다')
      } else {
        await ragGroupApi.createKey({
          rag_key: ragKey.trim(),
          rag_group: ragGroup.trim(),
          description: description.trim() || undefined,
          rag_type: ragType,
        })
        toast.success('인덱스가 생성되었습니다')
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
          <DialogTitle>{initial ? '인덱스 수정' : '인덱스 생성'}</DialogTitle>
        </DialogHeader>
        <div className='flex flex-col gap-4 py-2'>
          <div className='flex flex-col gap-1.5'>
            <Label>인덱스 ID *</Label>
            <Input
              value={ragKey}
              onChange={(e) => setRagKey(e.target.value)}
              placeholder='예: product-docs-v1'
              disabled={!!initial}
            />
            <p className='text-xs text-muted-foreground'>RAG 인덱스의 고유 식별자입니다.</p>
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label>그룹 *</Label>
            {groups.length > 0 ? (
              <select
                className='flex h-9 w-full items-center rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring'
                value={ragGroup}
                onChange={(e) => setRagGroup(e.target.value)}
              >
                {groups.map((g) => (
                  <option key={g.id} value={g.name}>{g.name}</option>
                ))}
              </select>
            ) : (
              <Input value={ragGroup} onChange={(e) => setRagGroup(e.target.value)} placeholder='그룹 이름' />
            )}
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label>타입</Label>
            <select
              className='flex h-9 w-full items-center rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring'
              value={ragType}
              onChange={(e) => setRagType(e.target.value)}
            >
              <option value='chatbot_shared'>Chatbot Shared</option>
              <option value='user_isolated'>User Isolated</option>
              <option value='natural_search'>Natural Search</option>
            </select>
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label>설명</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder='인덱스 설명 (선택)'
              rows={2}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant='outline' onClick={onClose}>취소</Button>
          <Button onClick={handleSave} disabled={saving || !ragKey.trim() || !ragGroup.trim()}>저장</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DeleteIndexDialog({ open, onClose, index, onDeleted }: {
  open: boolean; onClose: () => void; index: RagKey; onDeleted: () => void
}) {
  const [deleteDocs, setDeleteDocs] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await ragGroupApi.deleteKey(index.id, deleteDocs)
      toast.success(deleteDocs ? '인덱스와 문서가 삭제되었습니다' : '인덱스가 삭제되었습니다')
      onDeleted()
      onClose()
    } catch (e) {
      logger.error(e)
      toast.error('삭제에 실패했습니다')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={(o) => !o && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>인덱스 삭제</AlertDialogTitle>
          <AlertDialogDescription>
            <strong>{index.rag_key}</strong> 인덱스를 삭제합니다.
          </AlertDialogDescription>
          {index.doc_count > 0 && (
            <div className='flex items-center gap-2 rounded-md border p-3 mt-2'>
              <Switch checked={deleteDocs} onCheckedChange={setDeleteDocs} id='delete-docs-idx' />
              <Label htmlFor='delete-docs-idx' className='cursor-pointer text-sm'>
                문서 {index.doc_count}개와 임베딩도 함께 삭제
              </Label>
            </div>
          )}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>취소</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={deleting}
            className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
          >
            삭제
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

function IndexRow({ idx, groups, selected, onSelect, onRefresh }: {
  idx: RagKey; groups: RagGroup[]; selected: SelectedNode
  onSelect: (n: SelectedNode) => void; onRefresh: () => void
}) {
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const isSelected = selected.type === 'index' && selected.indexKey === idx.rag_key

  return (
    <>
      <div
        className={cn(
          'group flex items-center gap-2 pl-8 pr-2 py-1.5 cursor-pointer rounded-sm mx-1 text-sm',
          isSelected
            ? 'bg-primary/10 text-primary'
            : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'
        )}
        onClick={() => onSelect({ type: 'index', groupName: idx.rag_group, indexKey: idx.rag_key })}
      >
        <Layers className='h-3.5 w-3.5 shrink-0' />
        <span className='flex-1 font-mono truncate text-xs'>{idx.rag_key}</span>
        <span className='text-xs tabular-nums shrink-0'>{idx.doc_count}</span>
        <div className='hidden group-hover:flex gap-0.5 shrink-0' onClick={(e) => e.stopPropagation()}>
          <Button size='icon' variant='ghost' className='h-5 w-5' onClick={() => setEditOpen(true)}>
            <Pencil className='h-3 w-3' />
          </Button>
          <Button
            size='icon' variant='ghost'
            className='h-5 w-5 text-destructive hover:text-destructive'
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 className='h-3 w-3' />
          </Button>
        </div>
      </div>

      <IndexFormDialog open={editOpen} onClose={() => setEditOpen(false)} initial={idx} groups={groups} onSave={onRefresh} />
      <DeleteIndexDialog open={deleteOpen} onClose={() => setDeleteOpen(false)} index={idx} onDeleted={onRefresh} />
    </>
  )
}

function GroupRow({ group, keys, groups, selected, onSelect, onRefresh }: {
  group: RagGroup; keys: RagKey[]; groups: RagGroup[]
  selected: SelectedNode; onSelect: (n: SelectedNode) => void; onRefresh: () => void
}) {
  const [expanded, setExpanded] = useState(true)
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [addIndexOpen, setAddIndexOpen] = useState(false)

  const groupKeys = keys.filter((k) => k.rag_group === group.name)
  const isSelected = selected.type === 'group' && selected.groupName === group.name

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await ragGroupApi.deleteGroup(group.id)
      toast.success('그룹이 삭제되었습니다')
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
      <div>
        <div
          className={cn(
            'group flex items-center gap-2 px-2 py-1.5 cursor-pointer rounded-sm mx-1',
            isSelected ? 'bg-primary/10' : 'hover:bg-muted/50'
          )}
          onClick={() => onSelect({ type: 'group', groupName: group.name })}
        >
          <button
            type='button'
            className='text-muted-foreground hover:text-foreground shrink-0'
            onClick={(e) => { e.stopPropagation(); setExpanded((v) => !v) }}
          >
            {expanded
              ? <ChevronDown className='h-3.5 w-3.5' />
              : <ChevronRight className='h-3.5 w-3.5' />}
          </button>
          <div className='w-2.5 h-2.5 rounded-full shrink-0' style={{ backgroundColor: group.color }} />
          <FolderOpen className='h-3.5 w-3.5 text-muted-foreground shrink-0' />
          <span className={cn('flex-1 text-sm font-medium truncate', isSelected && 'text-primary')}>
            {group.name}
          </span>
          <span className='text-xs tabular-nums text-muted-foreground shrink-0'>{group.doc_count}</span>
          <div className='hidden group-hover:flex gap-0.5 shrink-0' onClick={(e) => e.stopPropagation()}>
            <Button size='icon' variant='ghost' className='h-5 w-5' title='인덱스 추가' onClick={() => setAddIndexOpen(true)}>
              <Plus className='h-3 w-3' />
            </Button>
            <Button size='icon' variant='ghost' className='h-5 w-5' onClick={() => setEditOpen(true)}>
              <Pencil className='h-3 w-3' />
            </Button>
            <Button
              size='icon' variant='ghost'
              className='h-5 w-5 text-destructive hover:text-destructive'
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className='h-3 w-3' />
            </Button>
          </div>
        </div>

        {expanded && groupKeys.map((idx) => (
          <IndexRow
            key={idx.id}
            idx={idx}
            groups={groups}
            selected={selected}
            onSelect={onSelect}
            onRefresh={onRefresh}
          />
        ))}
      </div>

      <GroupFormDialog open={editOpen} onClose={() => setEditOpen(false)} initial={group} onSave={onRefresh} />
      <IndexFormDialog
        open={addIndexOpen}
        onClose={() => setAddIndexOpen(false)}
        groups={groups}
        defaultGroup={group.name}
        onSave={onRefresh}
      />

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>그룹 삭제</AlertDialogTitle>
            <AlertDialogDescription>
              <strong>{group.name}</strong> 그룹을 삭제합니다. 하위 인덱스 설정이 함께 삭제되며 문서는 보존됩니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
            >
              삭제
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

export function TreePanel({ groups, keys, selected, onSelect, onRefresh }: TreePanelProps) {
  const [createGroupOpen, setCreateGroupOpen] = useState(false)
  const totalDocs = groups.reduce((s, g) => s + g.doc_count, 0)

  return (
    <div className='flex flex-col h-full'>
      <div className='flex items-center justify-between px-3 py-2 border-b'>
        <span className='text-xs font-semibold text-muted-foreground uppercase tracking-wider'>
          그룹 / 인덱스
        </span>
        <Button
          size='icon' variant='ghost' className='h-6 w-6'
          title='그룹 추가'
          onClick={() => setCreateGroupOpen(true)}
        >
          <Plus className='h-3.5 w-3.5' />
        </Button>
      </div>

      <div className='flex-1 overflow-y-auto py-1'>
        <div
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 cursor-pointer rounded-sm mx-1 text-sm',
            selected.type === 'all'
              ? 'bg-primary/10 text-primary font-medium'
              : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'
          )}
          onClick={() => onSelect({ type: 'all' })}
        >
          <Database className='h-3.5 w-3.5 shrink-0' />
          <span className='flex-1'>전체 문서</span>
          <span className='text-xs tabular-nums'>{totalDocs}</span>
        </div>

        {groups.length > 0 && <div className='my-1 border-t mx-2' />}

        {groups.length === 0 ? (
          <div className='px-3 py-6 text-xs text-muted-foreground text-center'>
            그룹이 없습니다.<br />+ 버튼으로 추가하세요.
          </div>
        ) : (
          groups.map((g) => (
            <GroupRow
              key={g.id}
              group={g}
              keys={keys}
              groups={groups}
              selected={selected}
              onSelect={onSelect}
              onRefresh={onRefresh}
            />
          ))
        )}
      </div>

      <GroupFormDialog
        open={createGroupOpen}
        onClose={() => setCreateGroupOpen(false)}
        onSave={onRefresh}
      />
    </div>
  )
}
