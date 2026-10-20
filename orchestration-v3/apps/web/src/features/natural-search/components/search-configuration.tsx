import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { LLM_MODELS, type LlmModel } from '@/config/models'
import { ragApi } from '@/api/rag'

interface SearchConfigurationProps {
  model: LlmModel
  setModel: (value: LlmModel) => void
  ragGroup: string
  setRagGroup: (value: string) => void
  systemPrompt: string
  setSystemPrompt: (value: string) => void
}

export function SearchConfiguration({
  model,
  setModel,
  ragGroup,
  setRagGroup,
  systemPrompt,
  setSystemPrompt,
}: SearchConfigurationProps) {
  const { data: groups = [] } = useQuery({
    queryKey: ['rag-groups'],
    queryFn: ragApi.getRagGroups,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Search Configuration</CardTitle>
      </CardHeader>
      <CardContent className='flex flex-col gap-4'>
        <div className='grid gap-4 md:grid-cols-2'>
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
            <label className='text-sm font-medium'>RAG Group</label>
            <select
              className='flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50'
              value={ragGroup}
              onChange={(e) => setRagGroup(e.target.value)}
            >
              <option value=''>-- Select Group --</option>
              {groups.map((g) => (
                <option key={g.id} value={g.name}>
                  {g.name}
                  {g.description ? ` — ${g.description}` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className='flex flex-col gap-2'>
          <label className='text-sm font-medium'>System Prompt</label>
          <Textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder='검색 결과를 요약할 때 사용할 시스템 프롬프트를 입력하세요. (비워두면 기본값 사용)'
            rows={4}
          />
        </div>
      </CardContent>
    </Card>
  )
}
