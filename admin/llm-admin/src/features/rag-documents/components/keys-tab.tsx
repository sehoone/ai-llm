'use client'

import { useState } from 'react'
import { Plus, Pencil, Trash2, FileText, Layers } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { toast } from 'sonner'
import { ragGroupApi, type RagKey, type RagGroup } from '@/api/rag-groups'
import { logger } from '@/lib/logger'

interface KeysTabProps {
  keys: RagKey[]
  groups: RagGroup[]
  onRefresh: () => void
}

interface CollectionFormDialogProps {
  open: boolean
  onClose: () => void
  initial?: RagKey
  groups: RagGroup[]
  onSave: () => void
}

function CollectionFormDialog({ open, onClose, initial, groups, onSave }: CollectionFormDialogProps) {
  const [ragKey, setRagKey] = useState(initial?.rag_key ?? '')
  const [ragGroup, setRagGroup] = useState(initial?.rag_group ?? (groups[0]?.name ?? ''))
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
        toast.success('컬렉션이 수정되었습니다')
      } else {
        await ragGroupApi.createKey({
          rag_key: ragKey.trim(),
          rag_group: ragGroup.trim(),
          description: description.trim() || undefined,
          rag_type: ragType,
        })
        toast.success('컬렉션이 생성되었습니다')
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
          <DialogTitle>{initial ? '컬렉션 수정' : '컬렉션 생성'}</DialogTitle>
        </DialogHeader>
        <div className='flex flex-col gap-4 py-2'>
          <div className='flex flex-col gap-1.5'>
            <Label>컬렉션 ID *</Label>
            <Input
              value={ragKey}
              onChange={(e) => setRagKey(e.target.value)}
              placeholder='예: product-docs-v1'
              disabled={!!initial}
            />
            <p className='text-xs text-muted-foreground'>문서 컬렉션의 고유 식별자입니다.</p>
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label>카테고리 *</Label>
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
              <Input
                value={ragGroup}
                onChange={(e) => setRagGroup(e.target.value)}
                placeholder='카테고리 이름'
              />
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
              placeholder='컬렉션 설명 (선택)'
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

interface DeleteCollectionDialogProps {
  open: boolean
  onClose: () => void
  collection: RagKey
  onDeleted: () => void
}

function DeleteCollectionDialog({ open, onClose, collection, onDeleted }: DeleteCollectionDialogProps) {
  const [deleteDocs, setDeleteDocs] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await ragGroupApi.deleteKey(collection.id, deleteDocs)
      toast.success(deleteDocs ? '컬렉션과 문서가 삭제되었습니다' : '컬렉션이 삭제되었습니다')
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
          <AlertDialogTitle>컬렉션 삭제</AlertDialogTitle>
          <AlertDialogDescription>
            <strong>{collection.rag_key}</strong> 컬렉션을 삭제합니다.
          </AlertDialogDescription>
          {collection.doc_count > 0 && (
            <div className='flex items-center gap-2 rounded-md border p-3 mt-2'>
              <Switch checked={deleteDocs} onCheckedChange={setDeleteDocs} id='delete-docs' />
              <Label htmlFor='delete-docs' className='cursor-pointer text-sm'>
                문서 {collection.doc_count}개와 임베딩도 함께 삭제
              </Label>
            </div>
          )}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onClose}>취소</AlertDialogCancel>
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

export function KeysTab({ keys, groups, onRefresh }: KeysTabProps) {
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [editCollection, setEditCollection] = useState<RagKey | null>(null)
  const [deleteCollection, setDeleteCollection] = useState<RagKey | null>(null)

  const filtered = keys.filter((k) => {
    const matchSearch = !search || k.rag_key.includes(search)
    const matchCategory = !categoryFilter || k.rag_group === categoryFilter
    return matchSearch && matchCategory
  })

  return (
    <div className='flex flex-col gap-4'>
      <div className='flex items-center gap-3'>
        <Input
          placeholder='컬렉션 검색'
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className='h-8 w-[200px]'
        />
        <select
          className='flex h-8 w-[160px] items-center rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring'
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value=''>전체 카테고리</option>
          {groups.map((g) => (
            <option key={g.id} value={g.name}>{g.name}</option>
          ))}
        </select>
        <span className='text-sm text-muted-foreground ml-auto'>{filtered.length}개</span>
        <Button size='sm' onClick={() => setCreateOpen(true)}>
          <Plus className='h-4 w-4 mr-1' />컬렉션 추가
        </Button>
      </div>

      <div className='rounded-md border'>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>컬렉션 ID</TableHead>
              <TableHead>카테고리</TableHead>
              <TableHead>타입</TableHead>
              <TableHead>문서</TableHead>
              <TableHead>설명</TableHead>
              <TableHead className='w-[80px]' />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className='text-center text-muted-foreground py-8'>
                  컬렉션이 없습니다
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((col) => (
                <TableRow key={col.id}>
                  <TableCell>
                    <span className='flex items-center gap-1.5'>
                      <Layers className='h-3.5 w-3.5 text-muted-foreground shrink-0' />
                      <span className='font-mono text-sm'>{col.rag_key}</span>
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant='secondary'
                      style={{
                        backgroundColor: groups.find((g) => g.name === col.rag_group)?.color + '22',
                        color: groups.find((g) => g.name === col.rag_group)?.color,
                        borderColor: groups.find((g) => g.name === col.rag_group)?.color + '44',
                      }}
                      className='border text-xs'
                    >
                      {col.rag_group}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant='outline' className='text-xs'>{col.rag_type}</Badge>
                  </TableCell>
                  <TableCell>
                    <span className='flex items-center gap-1 text-sm'>
                      <FileText className='h-3.5 w-3.5 text-muted-foreground' />{col.doc_count}
                    </span>
                  </TableCell>
                  <TableCell className='text-sm text-muted-foreground truncate max-w-[200px]'>
                    {col.description ?? '—'}
                  </TableCell>
                  <TableCell>
                    <div className='flex gap-1'>
                      <Button size='icon' variant='ghost' className='h-7 w-7' onClick={() => setEditCollection(col)}>
                        <Pencil className='h-3.5 w-3.5' />
                      </Button>
                      <Button
                        size='icon'
                        variant='ghost'
                        className='h-7 w-7 text-destructive hover:text-destructive'
                        onClick={() => setDeleteCollection(col)}
                      >
                        <Trash2 className='h-3.5 w-3.5' />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <CollectionFormDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        groups={groups}
        onSave={onRefresh}
      />

      {editCollection && (
        <CollectionFormDialog
          open={true}
          onClose={() => setEditCollection(null)}
          initial={editCollection}
          groups={groups}
          onSave={onRefresh}
        />
      )}

      {deleteCollection && (
        <DeleteCollectionDialog
          open={true}
          onClose={() => setDeleteCollection(null)}
          collection={deleteCollection}
          onDeleted={onRefresh}
        />
      )}
    </div>
  )
}
