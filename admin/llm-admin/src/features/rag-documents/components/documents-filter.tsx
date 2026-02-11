import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

interface DocumentsFilterProps {
  ragKey: string
  setRagKey: (value: string) => void
  ragType: string
  setRagType: (value: string) => void
  onApplyFilters: () => void
}

export function DocumentsFilter({
  ragKey,
  setRagKey,
  ragType,
  setRagType,
  onApplyFilters,
}: DocumentsFilterProps) {
  return (
    <div className='flex gap-4 mt-4'>
      <div className='w-[200px]'>
        <Input
          placeholder='Filter by RAG Key'
          value={ragKey}
          onChange={(e) => setRagKey(e.target.value)}
          className='h-8'
        />
      </div>
      <div className='w-[200px]'>
        <select
          className='flex h-8 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50'
          value={ragType}
          onChange={(e) => setRagType(e.target.value)}
        >
          <option value=''>All Types</option>
          <option value='user_isolated'>User Isolated</option>
          <option value='chatbot_shared'>Chatbot Shared</option>
          <option value='natural_search'>Natural Search</option>
        </select>
      </div>
      <Button size='sm' onClick={onApplyFilters}>
        Apply Filters
      </Button>
    </div>
  )
}
