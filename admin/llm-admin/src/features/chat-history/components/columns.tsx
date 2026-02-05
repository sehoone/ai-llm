'use client'

import { type ColumnDef } from '@tanstack/react-table'
import { type ChatHistoryResponse } from '@/types/chat-api'
import { format } from 'date-fns'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { ArrowRight } from 'lucide-react'

export const columns: ColumnDef<ChatHistoryResponse>[] = [
  {
    accessorKey: 'created_at',
    header: 'Date',
    cell: ({ row }) => {
      const date = new Date(row.getValue('created_at'))
      return <div className="text-nowrap">{format(date, 'yyyy-MM-dd HH:mm:ss')}</div>
    },
  },
  {
    accessorKey: 'user_email',
    header: 'User',
  },
  {
    accessorKey: 'session_name',
    header: 'Session',
    cell: ({ row }) => {
      const name = row.getValue('session_name') as string
      const id = row.original.session_id
      return (
        <div className="flex flex-col">
          <span className="font-medium">{name || 'No Name'}</span>
          <span className="text-xs text-muted-foreground">{id.substring(0, 8)}...</span>
        </div>
      )
    },
  },
  {
    accessorKey: 'question',
    header: 'Question',
    cell: ({ row }) => {
      return (
        <div className="max-w-[300px] truncate" title={row.getValue('question')}>
          {row.getValue('question')}
        </div>
      )
    },
  },
  {
    accessorKey: 'answer',
    header: 'Answer',
    cell: ({ row }) => {
       return (
        <div className="max-w-[400px] truncate" title={row.getValue('answer')}>
          {row.getValue('answer')}
        </div>
      )
    },
  },
  {
    id: 'actions',
    cell: ({ row }) => {
      return (
        <Button variant="ghost" size="icon" asChild>
          <Link href={`/chat-history/${row.original.id}`}>
            <ArrowRight className="h-4 w-4" />
            <span className="sr-only">View detail</span>
          </Link>
        </Button>
      )
    },
  },
]
