import { Badge } from '@/components/ui/badge'

export function Section({
  title,
  endpoint,
  method = 'GET',
  children,
}: {
  title: string
  endpoint: string
  method?: string
  children: React.ReactNode
}) {
  return (
    <div className='rounded-lg border p-4'>
      <div className='mb-3 flex flex-wrap items-center gap-2'>
        <span className='text-sm font-semibold'>{title}</span>
        <Badge variant='outline' className='font-mono text-xs'>
          {method} {endpoint}
        </Badge>
      </div>
      {children}
    </div>
  )
}

export function JsonResult({ data }: { data: unknown }) {
  if (data === null || data === undefined) return null
  return (
    <pre className='mt-2 max-h-60 overflow-auto rounded-md bg-muted p-3 text-xs'>
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

export function ErrorMsg({ error }: { error: string | null }) {
  if (!error) return null
  return <p className='mt-2 text-xs text-destructive'>{error}</p>
}
