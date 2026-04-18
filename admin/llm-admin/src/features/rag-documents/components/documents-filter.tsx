import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

interface DocumentsFilterProps {
  ragKey: string
  setRagKey: (value: string) => void
  ragGroup: string
  setRagGroup: (value: string) => void
  ragType: string
  setRagType: (value: string) => void
  onApplyFilters: () => void
  availableGroups: string[]
}

export function DocumentsFilter({
  ragKey,
  setRagKey,
  ragGroup,
  setRagGroup,
  ragType,
  setRagType,
  onApplyFilters,
  availableGroups,
}: DocumentsFilterProps) {
  const handleReset = () => {
    setRagKey('')
    setRagGroup('')
    setRagType('')
    onApplyFilters()
  }

  return (
    <div className='flex flex-wrap gap-3 mt-4'>
      <Input
        placeholder='RAG Key 검색'
        value={ragKey}
        onChange={(e) => setRagKey(e.target.value)}
        className='h-8 w-[180px]'
      />

      <select
        className='flex h-8 w-[180px] items-center rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring'
        value={ragGroup}
        onChange={(e) => setRagGroup(e.target.value)}
      >
        <option value=''>전체 카테고리</option>
        {availableGroups.map((g) => (
          <option key={g} value={g}>{g}</option>
        ))}
      </select>

      <select
        className='flex h-8 w-[180px] items-center rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring'
        value={ragType}
        onChange={(e) => setRagType(e.target.value)}
      >
        <option value=''>전체 타입</option>
        <option value='user_isolated'>User Isolated</option>
        <option value='chatbot_shared'>Chatbot Shared</option>
        <option value='natural_search'>Natural Search</option>
      </select>

      <Button size='sm' onClick={onApplyFilters}>검색</Button>
      {(ragKey || ragGroup || ragType) && (
        <Button size='sm' variant='ghost' onClick={handleReset}>초기화</Button>
      )}
    </div>
  )
}
