import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LLM_MODELS, type LlmModel } from '@/config/models'

interface SearchConfigurationProps {
  model: LlmModel
  setModel: (value: LlmModel) => void
  ragType: 'user_isolated' | 'chatbot_shared' | 'natural_search'
  setRagType: (value: 'user_isolated' | 'chatbot_shared' | 'natural_search') => void
  ragKey: string
  setRagKey: (value: string) => void
  ragGroup: string
  setRagGroup: (value: string) => void
}

export function SearchConfiguration({
  model,
  setModel,
  ragType,
  setRagType,
  ragKey,
  setRagKey,
  ragGroup,
  setRagGroup,
}: SearchConfigurationProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Search Configuration</CardTitle>
      </CardHeader>
      <CardContent className='grid gap-4 md:grid-cols-4'>
        <div className='flex flex-col gap-2'>
          <label className='text-sm font-medium'>Model</label>
          <select
            className='flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50'
            value={model}
            onChange={(e) => setModel(e.target.value as LlmModel)}
          >
            {LLM_MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
        <div className='flex flex-col gap-2'>
          <label className='text-sm font-medium'>RAG Type</label>
          <select
            className='flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50'
            value={ragType}
            onChange={(e) => setRagType(e.target.value as never)}
          >
            <option value='natural_search'>Natural Search</option>
            <option value='user_isolated'>User Isolated</option>
            <option value='chatbot_shared'>Chatbot Shared</option>
          </select>
        </div>
        <div className='flex flex-col gap-2'>
          <label className='text-sm font-medium'>RAG Key</label>
          <Input
            value={ragKey}
            onChange={(e) => setRagKey(e.target.value)}
            placeholder='ex. default'
          />
        </div>
        <div className='flex flex-col gap-2'>
          <label className='text-sm font-medium'>RAG Group</label>
          <Input
            value={ragGroup}
            onChange={(e) => setRagGroup(e.target.value)}
            placeholder='Optional'
          />
        </div>
      </CardContent>
    </Card>
  )
}
