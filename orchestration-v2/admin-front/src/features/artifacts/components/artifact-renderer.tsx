'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { markdownComponents } from '@/components/markdown-components'

import { SandboxFrame } from './sandbox-frame'

/** The types that execute/render inside the sandboxed iframe. */
const SANDBOXED = new Set([
  'text/html',
  'application/vnd.react',
  'image/svg+xml',
  'application/vnd.mermaid',
])

type DataRecord = Record<string, unknown>

interface ArtifactRendererProps {
  type: string
  content: string
  dataGet?: () => Promise<DataRecord>
  dataSet?: (data: DataRecord) => Promise<void>
}

export function ArtifactRenderer({ type, content, dataGet, dataSet }: ArtifactRendererProps) {
  if (SANDBOXED.has(type)) {
    return <SandboxFrame type={type} content={content} dataGet={dataGet} dataSet={dataSet} />
  }

  if (type === 'text/markdown') {
    return (
      <div className='h-full overflow-auto p-6 text-sm'>
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {content}
        </ReactMarkdown>
      </div>
    )
  }

  // application/vnd.code and any unknown type → shown, not executed.
  return (
    <div className='h-full overflow-auto bg-zinc-950 p-4'>
      <pre className='overflow-x-auto'>
        <code className='font-mono text-sm leading-relaxed text-zinc-100'>{content}</code>
      </pre>
    </div>
  )
}
