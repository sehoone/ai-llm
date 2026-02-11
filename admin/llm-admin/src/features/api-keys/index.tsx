import { useEffect, useState } from 'react'
import { Plus, Copy, Trash2, Loader2 } from 'lucide-react'
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
import { logger } from '@/lib/logger'
import { ApiKeyCreateDialog } from './components/api-key-create-dialog'
import { ConfirmDialog } from '@/components/confirm-dialog'
import type { ApiKey } from '@/features/api-keys/data/schema'

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [revokeId, setRevokeId] = useState<number | null>(null)
  const [isRevoking, setIsRevoking] = useState(false)

  const fetchKeys = async () => {
    try {
      setIsLoading(true)
      const data = await getApiKeys()
       // Type assertion or data transformation if needed, usually schema matches api
      setKeys(data as unknown as ApiKey[])
    } catch (error) {
      logger.error(error)
      toast.error('Failed to fetch API keys')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchKeys()
  }, [])

  const handleCreate = async (values: { name: string; expires_at?: Date }) => {
    try {
      await createApiKey({
        name: values.name,
        expires_at: values.expires_at ? values.expires_at.toISOString() : undefined
      })
      toast.success('API Key created successfully')
      setIsCreateOpen(false)
      fetchKeys()
    } catch (error) {
      logger.error(error)
      toast.error('Failed to create API key')
    }
  }

  const handleConfirmRevoke = async () => {
    if (revokeId === null) return
    
    try {
      setIsRevoking(true)
      await revokeApiKey(revokeId)
      toast.success('API Key revoked successfully')
      fetchKeys()
    } catch (error) {
      logger.error(error)
      toast.error('Failed to revoke API key')
    } finally {
      setIsRevoking(false)
      setRevokeId(null)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('API Key copied to clipboard')
  }

  return (
    <div className='flex flex-col gap-4 p-4 md:p-8'>
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold tracking-tight'>Auth Keys</h2>
          <p className='text-muted-foreground'>
            Manage your API authentication keys.
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
            A list of your API keys.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Key</TableHead>
                <TableHead>Created At</TableHead>
                <TableHead>Expires At</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className='text-right'>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className='h-24 text-center'>
                    <Loader2 className='mx-auto h-6 w-6 animate-spin' />
                  </TableCell>
                </TableRow>
              ) : keys.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className='h-24 text-center'>
                    No API keys found. Create one to get started.
                  </TableCell>
                </TableRow>
              ) : (
                keys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className='font-medium'>{key.name}</TableCell>
                    <TableCell className='font-mono text-xs'>
                      {key.key.substring(0, 8)}...
                      <Button
                        variant='ghost'
                        size='icon'
                        className='ml-2 h-6 w-6'
                        onClick={() => copyToClipboard(key.key)}
                      >
                        <Copy className='h-3 w-3' />
                        <span className='sr-only'>Copy API Key</span>
                      </Button>
                    </TableCell>
                    <TableCell>
                      {format(new Date(key.created_at), 'MMM d, yyyy')}
                    </TableCell>
                    <TableCell>
                      {key.expires_at
                        ? format(new Date(key.expires_at), 'MMM d, yyyy')
                        : 'Never'}
                    </TableCell>
                    <TableCell>
                      <div
                        className={cn(
                          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
                          key.is_active
                            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
                            : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
                        )}
                      >
                        {key.is_active ? 'Active' : 'Revoked'}
                      </div>
                    </TableCell>
                    <TableCell className='text-right'>
                      <Button
                        variant='ghost'
                        size='icon'
                        className='text-destructive hover:text-destructive/90'
                        onClick={() => setRevokeId(key.id)}
                        disabled={!key.is_active}
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

      <ConfirmDialog
        open={!!revokeId}
        onOpenChange={(open) => !open && setRevokeId(null)}
        title="Are you absolutely sure?"
        desc="This action cannot be undone. This will permanently revoke the API key and any applications using it will no longer be able to authenticate."
        confirmText="Revoke Key"
        // destructive={true}
        handleConfirm={handleConfirmRevoke}
        isLoading={isRevoking}
      />
    </div>
  )
}
