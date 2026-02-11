import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Loader2, Trash2, FileText, Calendar, Eye } from 'lucide-react'
import { format } from 'date-fns'
import { type DocumentResponse } from '@/api/rag'

interface DocumentsTableProps {
  documents: DocumentResponse[]
  loading: boolean
  deletingId: number | null
  onDelete: (id: number) => void
  onView: (doc: DocumentResponse) => void
  formatFileSize: (bytes: number) => string
}

export function DocumentsTable({
  documents,
  loading,
  deletingId,
  onDelete,
  onView,
  formatFileSize,
}: DocumentsTableProps) {
  if (loading) {
    return (
      <div className='flex h-40 items-center justify-center'>
        <Loader2 className='h-8 w-8 animate-spin text-muted-foreground' />
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div className='flex h-40 flex-col items-center justify-center text-muted-foreground'>
        <FileText className='mb-2 h-10 w-10 opacity-20' />
        <p>No documents found</p>
      </div>
    )
  }

  return (
    <div className='rounded-md border'>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Filename</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Key</TableHead>
            <TableHead>Group</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Created At</TableHead>
            <TableHead className='text-right'>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id}>
              <TableCell className='font-medium'>
                <div className='flex items-center gap-2'>
                  <FileText className='h-4 w-4 text-blue-500' />
                  {doc.filename}
                </div>
              </TableCell>
              <TableCell>
                <Badge variant='outline'>{doc.rag_type}</Badge>
              </TableCell>
              <TableCell>{doc.rag_key}</TableCell>
              <TableCell>{doc.rag_group}</TableCell>
              <TableCell>{formatFileSize(doc.size)}</TableCell>
              <TableCell>
                <div className='flex items-center gap-2 text-muted-foreground'>
                  <Calendar className='h-3 w-3' />
                  {doc.created_at
                    ? format(new Date(doc.created_at), 'yyyy-MM-dd HH:mm')
                    : '-'}
                </div>
              </TableCell>
              <TableCell className='text-right'>
                <div className='flex items-center justify-end gap-2'>
                  <Button
                    variant='ghost'
                    size='icon'
                    onClick={() => onView(doc)}
                  >
                    <Eye className='h-4 w-4' />
                  </Button>
                  <Button
                    variant='ghost'
                    size='icon'
                    onClick={() => onDelete(doc.id)}
                    disabled={deletingId === doc.id}
                  >
                    {deletingId === doc.id ? (
                      <Loader2 className='h-4 w-4 animate-spin' />
                    ) : (
                      <Trash2 className='h-4 w-4 text-destructive' />
                    )}
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
