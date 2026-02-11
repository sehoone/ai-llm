import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface UploadConfigurationProps {
  ragType: 'user_isolated' | 'chatbot_shared' | 'natural_search'
  setRagType: (
    value: 'user_isolated' | 'chatbot_shared' | 'natural_search'
  ) => void
  ragKey: string
  setRagKey: (value: string) => void
  ragGroup: string
  setRagGroup: (value: string) => void
  tags: string
  setTags: (value: string) => void
}

export function UploadConfiguration({
  ragType,
  setRagType,
  ragKey,
  setRagKey,
  ragGroup,
  setRagGroup,
  tags,
  setTags,
}: UploadConfigurationProps) {
  return (
    <div className='grid gap-4 md:grid-cols-2'>
      <div className='space-y-2'>
        <Label htmlFor='rag_type'>RAG Type</Label>
        <Select
          value={ragType}
          onValueChange={(val: never) => setRagType(val)}
        >
          <SelectTrigger>
            <SelectValue placeholder='Select type' />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value='natural_search'>
              Natural Search (Knowledge Base)
            </SelectItem>
            <SelectItem value='user_isolated'>
              User Isolated (Private)
            </SelectItem>
            <SelectItem value='chatbot_shared'>
              Chatbot Shared (Global)
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className='space-y-2'>
        <Label htmlFor='rag_key'>RAG Key</Label>
        <Input
          id='rag_key'
          placeholder='e.g. project-x-docs'
          value={ragKey}
          onChange={(e) => setRagKey(e.target.value)}
          required
        />
        <p className='text-xs text-muted-foreground'>
          Unique identifier for this collection of documents.
        </p>
      </div>

      <div className='space-y-2'>
        <Label htmlFor='rag_group'>RAG Group</Label>
        <Input
          id='rag_group'
          placeholder='Optional (e.g. engineering)'
          value={ragGroup}
          onChange={(e) => setRagGroup(e.target.value)}
        />
      </div>

      <div className='space-y-2'>
        <Label htmlFor='tags'>Tags</Label>
        <Input
          id='tags'
          placeholder='Comma separated tags'
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />
      </div>
    </div>
  )
}
