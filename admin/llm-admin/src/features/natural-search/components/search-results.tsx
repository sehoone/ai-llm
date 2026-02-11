import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { type RAGSearchResult } from '@/api/rag'

interface SearchResultsProps {
  searching: boolean
  hasStarted: boolean
  summary: string
  results: RAGSearchResult[]
}

export function SearchResults({
  searching,
  hasStarted,
  summary,
  results,
}: SearchResultsProps) {
  if (searching) {
    return (
      <div className='space-y-4 pt-4'>
        <div className='space-y-2'>
          <Skeleton className='h-4 w-[250px]' />
          <Skeleton className='h-4 w-[200px]' />
        </div>
        <Skeleton className='h-[125px] w-full rounded-xl' />
      </div>
    )
  }

  if (hasStarted && !searching) {
    return (
      <div className='grid gap-6 md:grid-cols-3 pt-4'>
        {/* Main Result Area */}
        <div className='md:col-span-2 space-y-6'>
          <Card className='bg-muted/50 border-primary/20'>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                ✨ AI Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className='leading-relaxed whitespace-pre-wrap'>{summary}</p>
            </CardContent>
          </Card>
        </div>

        {/* Source Documents Area */}
        <div className='space-y-4'>
          <h3 className='font-semibold text-lg'>Sources</h3>
          {results.map((result, idx) => (
            <Card key={idx} className='overflow-hidden'>
              <CardHeader className='p-4 pb-2'>
                <CardTitle
                  className='text-sm font-medium truncate'
                  title={result.filename}
                >
                  {result.filename || `Document ${result.doc_id}`}
                </CardTitle>
                <div className='flex items-center gap-2 text-xs text-muted-foreground'>
                  <Badge variant='secondary' className='text-xs'>
                    {Math.round(result.similarity * 100)}% Match
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className='p-4 pt-2'>
                <p className='text-xs text-muted-foreground line-clamp-3'>
                  {result.content}
                </p>
              </CardContent>
            </Card>
          ))}
          {results.length === 0 && (
            <p className='text-sm text-muted-foreground'>No sources found.</p>
          )}
        </div>
      </div>
    )
  }

  return null
}
