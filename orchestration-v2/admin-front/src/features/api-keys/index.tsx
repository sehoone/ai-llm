import { useEffect, useState } from 'react'
import { Plus, Copy, Trash2, Loader2, KeyRound, X } from 'lucide-react'
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
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { cn } from '@/lib/utils'
import { getApiKeys, createApiKey, revokeApiKey, type ApiKey } from '@/api/api-keys'
import { logger } from '@/lib/logger'
import { ApiKeyCreateDialog } from './components/api-key-create-dialog'
import { ConfirmDialog } from '@/components/confirm-dialog'

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [revokeId, setRevokeId] = useState<number | null>(null)
  const [isRevoking, setIsRevoking] = useState(false)
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null)

  const fetchKeys = async () => {
    try {
      setIsLoading(true)
      const data = await getApiKeys()
      setKeys(data)
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

  const handleCreate = async (values: { name: string; expiresAt?: Date }) => {
    try {
      const created = await createApiKey({
        name: values.name,
        // ISO with Z fails LocalDateTime deserialization — strip timezone
        expiresAt: values.expiresAt
          ? format(values.expiresAt, "yyyy-MM-dd'T'HH:mm:ss")
          : undefined,
      })
      setIsCreateOpen(false)
      setNewlyCreatedKey(created.key)
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
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text)
    } else {
      const el = document.createElement('textarea')
      el.value = text
      el.style.position = 'fixed'
      el.style.opacity = '0'
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    toast.success('Copied to clipboard')
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

      {/* One-time key reveal — shown only right after creation */}
      {newlyCreatedKey && (
        <Alert className='border-green-500 bg-green-50 dark:bg-green-950/20'>
          <KeyRound className='h-4 w-4 text-green-600' />
          <AlertTitle className='text-green-800 dark:text-green-400'>
            API Key Created — Copy it now!
          </AlertTitle>
          <AlertDescription>
            <p className='mb-2 text-sm text-green-700 dark:text-green-300'>
              This is the only time the full key will be shown. Store it somewhere safe.
            </p>
            <div className='flex items-center gap-2 rounded-md border border-green-300 bg-white px-3 py-2 dark:bg-green-950/40'>
              <code className='flex-1 truncate text-xs font-mono text-green-900 dark:text-green-200'>
                {newlyCreatedKey}
              </code>
              <Button
                size='sm'
                variant='outline'
                className='shrink-0 border-green-400 text-green-700 hover:bg-green-100'
                onClick={() => copyToClipboard(newlyCreatedKey)}
              >
                <Copy className='mr-1 h-3 w-3' /> Copy
              </Button>
              <Button
                size='icon'
                variant='ghost'
                className='shrink-0 h-8 w-8 text-green-600 hover:bg-green-100'
                onClick={() => setNewlyCreatedKey(null)}
              >
                <X className='h-4 w-4' />
                <span className='sr-only'>Dismiss</span>
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

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
                      {key.key}
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
                          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
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

      <ConfirmDialog
        open={!!revokeId}
        onOpenChange={(open) => !open && setRevokeId(null)}
        title='Are you absolutely sure?'
        desc='This action cannot be undone. This will permanently revoke the API key and any applications using it will no longer be able to authenticate.'
        confirmText='Revoke Key'
        handleConfirm={handleConfirmRevoke}
        isLoading={isRevoking}
      />
    </div>
  )
}
