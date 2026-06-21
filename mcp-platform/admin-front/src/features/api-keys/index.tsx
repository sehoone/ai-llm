'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Loader2 } from 'lucide-react'
import { format } from 'date-fns'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { getApiKeys, createApiKey, revokeApiKey } from '@/api/api-keys'
import type { CreateApiKeyRequest } from '@/api/api-keys'
import { logger } from '@/lib/logger'
import { ApiKeyCreateDialog } from './components/api-key-create-dialog'
import { ApiKeyCreatedDialog } from './components/api-key-created-dialog'
import { ConfirmDialog } from '@/components/confirm-dialog'
import type { ApiKey } from '@/features/api-keys/data/schema'

export default function ApiKeys() {
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [createdKey, setCreatedKey] = useState<ApiKey | null>(null)
  const [revokeId, setRevokeId] = useState<number | null>(null)

  const { data: keys = [], isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: getApiKeys,
  })

  const createMutation = useMutation({
    mutationFn: (values: CreateApiKeyRequest) => createApiKey(values),
    onSuccess: (newKey) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setIsCreateOpen(false)
      setCreatedKey(newKey)
    },
    onError: (error) => {
      logger.error(error)
      toast.error('Failed to create API key')
    },
  })

  const revokeMutation = useMutation({
    mutationFn: (id: number) => revokeApiKey(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      toast.success('API Key revoked successfully')
      setRevokeId(null)
    },
    onError: (error) => {
      logger.error(error)
      toast.error('Failed to revoke API key')
    },
  })

  const handleCreate = async (values: { name: string; expiresAt?: Date }) => {
    await createMutation.mutateAsync({
      name: values.name,
      expiresAt: values.expiresAt ? values.expiresAt.toISOString() : undefined,
    })
  }

  return (
    <div className='flex flex-col gap-4 p-4 md:p-8'>
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold tracking-tight'>API Keys</h2>
          <p className='text-muted-foreground'>
            Manage your MCP authentication keys.
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)}>
          <Plus className='mr-2 h-4 w-4' /> Create New Key
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
          <CardDescription>
            A list of your API keys. Keys are masked after creation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Key</TableHead>
                <TableHead>Usage</TableHead>
                <TableHead>Last Used</TableHead>
                <TableHead>Created At</TableHead>
                <TableHead>Expires At</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className='text-right'>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className='h-24 text-center'>
                    <Loader2 className='mx-auto h-6 w-6 animate-spin' />
                  </TableCell>
                </TableRow>
              ) : keys.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className='h-24 text-center'>
                    No API keys found. Create one to get started.
                  </TableCell>
                </TableRow>
              ) : (
                keys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className='font-medium'>{key.name}</TableCell>
                    <TableCell className='font-mono text-xs'>
                      {key.key}
                    </TableCell>
                    <TableCell className='text-sm tabular-nums'>
                      {key.usageCount ?? 0}
                    </TableCell>
                    <TableCell className='text-sm'>
                      {key.lastUsedAt
                        ? format(new Date(key.lastUsedAt), 'MMM d, yyyy HH:mm')
                        : '—'}
                    </TableCell>
                    <TableCell>
                      {format(new Date(key.createdAt), 'MMM d, yyyy')}
                    </TableCell>
                    <TableCell>
                      {key.expiresAt
                        ? format(new Date(key.expiresAt), 'MMM d, yyyy')
                        : 'Never'}
                    </TableCell>
                    <TableCell>
                      <div
                        className={cn(
                          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
                          key.isActive
                            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
                            : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
                        )}
                      >
                        {key.isActive ? 'Active' : 'Revoked'}
                      </div>
                    </TableCell>
                    <TableCell className='text-right'>
                      <Button
                        variant='ghost'
                        size='icon'
                        className='text-destructive hover:text-destructive/90'
                        onClick={() => setRevokeId(key.id)}
                        disabled={!key.isActive}
                      >
                        <Trash2 className='h-4 w-4' />
                        <span className='sr-only'>Revoke</span>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <ApiKeyCreateDialog
        open={isCreateOpen}
        onOpenChange={setIsCreateOpen}
        onSubmit={handleCreate}
      />

      {createdKey && (
        <ApiKeyCreatedDialog
          open={!!createdKey}
          onOpenChange={(open) => !open && setCreatedKey(null)}
          apiKey={createdKey.key}
          keyName={createdKey.name}
        />
      )}

      <ConfirmDialog
        open={!!revokeId}
        onOpenChange={(open) => !open && setRevokeId(null)}
        title='Are you absolutely sure?'
        desc='This action cannot be undone. This will permanently revoke the API key and any applications using it will no longer be able to authenticate.'
        confirmText='Revoke Key'
        handleConfirm={() => revokeId !== null && revokeMutation.mutate(revokeId)}
        isLoading={revokeMutation.isPending}
      />
    </div>
  )
}
