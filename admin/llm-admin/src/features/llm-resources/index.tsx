import { useEffect, useState } from 'react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { getLLMResources, createLLMResource, updateLLMResource, deleteLLMResource } from '@/api/llm-resources'
import type { LLMResource } from './data/schema'
import { LLMResourceDialog } from './components/llm-resource-dialog'
import { toast } from 'sonner'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { logger } from '@/lib/logger'

export default function LLMResources() {
  const [resources, setResources] = useState<LLMResource[]>([])
  const [open, setOpen] = useState(false)
  const [selectedResource, setSelectedResource] = useState<LLMResource | undefined>()
  const [deleteId, setDeleteId] = useState<number | null>(null)

  useEffect(() => {
    fetchResources()
  }, [])

  const fetchResources = async () => {
    try {
      const data = await getLLMResources()
      setResources(data)
    } catch (e) {
      logger.error('Failed to fetch resources', e as Error)
    }
  }

  const handleEdit = (resource: LLMResource) => {
    setSelectedResource(resource)
    setOpen(true)
  }

  const handleAdd = () => {
    setSelectedResource(undefined)
    setOpen(true)
  }

  const handleDelete = async () => {
    if (deleteId) {
       try {
        await deleteLLMResource(deleteId)
        fetchResources()
        toast.success('Resource deleted')
      } catch (e) {
         logger.error('Failed to delete resource', e as Error)
      } finally {
        setDeleteId(null)
      }
    }
  }

  const handleSubmit = async (data: LLMResource) => {
    try {
      if (selectedResource && selectedResource.id) {
        await updateLLMResource(selectedResource.id, data)
        toast.success('Resource updated')
      } else {
        await createLLMResource(data)
        toast.success('Resource created')
      }
      fetchResources()
    } catch (e) {
      logger.error('Failed to save resource', e as Error)
    }
  }

  return (
    <div className='flex flex-col gap-4 p-4 md:p-8'>
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold tracking-tight'>LLM Resources</h2>
          <p className='text-muted-foreground'>
            Manage your LLM resources for failover and fallback.
          </p>
        </div>
        <div>
          <Button onClick={handleAdd}>
            <Plus className='mr-2 h-4 w-4' /> Add Resource
          </Button>
        </div>
      </div>
      <Card>
        <CardHeader>
           <CardTitle>Resources</CardTitle>
           <CardDescription>List of available LLM endpoints</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Region</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {resources.map((resource) => (
                <TableRow key={resource.id}>
                  <TableCell className="font-medium">{resource.name}</TableCell>
                  <TableCell>{resource.provider}</TableCell>
                  <TableCell>{resource.region || '-'}</TableCell>
                  <TableCell>{resource.priority}</TableCell>
                  <TableCell>{resource.is_active ? 'Active' : 'Inactive'}</TableCell>
                   <TableCell className="text-right space-x-2">
                      <Button variant="outline" size="sm" onClick={() => handleEdit(resource)}>Edit</Button>
                      <Button variant="destructive" size="sm" onClick={() => setDeleteId(resource.id!)}>Delete</Button>
                   </TableCell>
                </TableRow>
              ))}
              {resources.length === 0 && (
                  <TableRow>
                      <TableCell colSpan={6} className="text-center h-24">No resources found.</TableCell>
                  </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <LLMResourceDialog
        open={open}
        onOpenChange={setOpen}
        resource={selectedResource}
        onSubmit={handleSubmit}
      />
      
      <ConfirmDialog
        open={!!deleteId}
        onOpenChange={(open) => !open && setDeleteId(null)}
        handleConfirm={handleDelete}
        title="Delete Resource"
        desc="Are you sure you want to delete this resource? This action cannot be undone."
      />
    </div>
  )
}
