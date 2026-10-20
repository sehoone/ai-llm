import { Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface SearchInputProps {
  query: string
  setQuery: (value: string) => void
  handleSearch: (e: React.FormEvent) => void
  loading: boolean
  searching: boolean
}

export function SearchInput({
  query,
  setQuery,
  handleSearch,
  loading,
  searching,
}: SearchInputProps) {
  return (
    <div className='relative'>
      <form onSubmit={handleSearch} className='flex w-full items-center space-x-2'>
        <Input
          className='flex-1 text-lg h-12'
          placeholder='Ask anything...'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Button
          type='submit'
          size='lg'
          disabled={loading}
          className='h-12 w-24'
        >
          {searching ? 'Search...' : <Search className='h-5 w-5' />}
        </Button>
      </form>
    </div>
  )
}
