'use client'

/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable react-refresh/only-export-components */
import { useState } from 'react'

import { Check, Copy } from 'lucide-react'

const CodeBlock = ({
  language,
  children,
}: {
  language: string
  children: string
}) => {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(children)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className='my-4 overflow-hidden rounded-xl border border-zinc-700 bg-zinc-950'>
      <div className='flex items-center justify-between border-b border-zinc-700 bg-zinc-900 px-4 py-2'>
        <span className='font-mono text-xs text-zinc-400'>
          {language || 'text'}
        </span>
        <button
          type='button'
          onClick={copy}
          className='flex items-center gap-1.5 rounded px-2 py-0.5 text-xs text-zinc-400 transition-colors hover:bg-zinc-700 hover:text-zinc-100'
        >
          {copied ? (
            <>
              <Check className='h-3 w-3 text-green-400' />
              <span className='text-green-400'>복사됨</span>
            </>
          ) : (
            <>
              <Copy className='h-3 w-3' />
              <span>복사</span>
            </>
          )}
        </button>
      </div>
      <pre className='overflow-x-auto p-4'>
        <code className='font-mono text-sm leading-relaxed text-zinc-100'>
          {children}
        </code>
      </pre>
    </div>
  )
}

export const markdownComponents = {
  pre: ({ children }: any) => <>{children}</>,
  code: ({ node, className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || '')
    const codeString = String(children).replace(/\n$/, '')
    if (match || codeString.includes('\n')) {
      return (
        <CodeBlock language={match?.[1] ?? ''}>{codeString}</CodeBlock>
      )
    }
    return (
      <code
        className='rounded bg-muted px-1.5 py-0.5 font-mono text-[0.875em] text-foreground'
        {...props}
      >
        {children}
      </code>
    )
  },

  h1: ({ node, children, ...props }: any) => (
    <h1
      className='mb-4 mt-6 border-b border-border pb-2 text-2xl font-bold first:mt-0'
      {...props}
    >
      {children}
    </h1>
  ),
  h2: ({ node, children, ...props }: any) => (
    <h2
      className='mb-3 mt-5 border-b border-border pb-1.5 text-xl font-semibold first:mt-0'
      {...props}
    >
      {children}
    </h2>
  ),
  h3: ({ node, children, ...props }: any) => (
    <h3 className='mb-2 mt-4 text-lg font-semibold first:mt-0' {...props}>
      {children}
    </h3>
  ),
  h4: ({ node, children, ...props }: any) => (
    <h4 className='mb-2 mt-3 text-base font-semibold first:mt-0' {...props}>
      {children}
    </h4>
  ),
  h5: ({ node, children, ...props }: any) => (
    <h5 className='mb-1.5 mt-2 text-sm font-semibold first:mt-0' {...props}>
      {children}
    </h5>
  ),
  h6: ({ node, children, ...props }: any) => (
    <h6
      className='mb-1 mt-2 text-sm font-medium text-muted-foreground first:mt-0'
      {...props}
    >
      {children}
    </h6>
  ),

  p: ({ node, children, ...props }: any) => (
    <p className='mb-3 leading-7 last:mb-0' {...props}>
      {children}
    </p>
  ),

  ul: ({ node, children, ...props }: any) => (
    <ul className='my-3 ml-5 list-disc space-y-1 leading-7' {...props}>
      {children}
    </ul>
  ),
  ol: ({ node, children, ...props }: any) => (
    <ol className='my-3 ml-5 list-decimal space-y-1 leading-7' {...props}>
      {children}
    </ol>
  ),
  li: ({ node, children, ...props }: any) => (
    <li className='pl-1' {...props}>
      {children}
    </li>
  ),

  blockquote: ({ node, children, ...props }: any) => (
    <blockquote
      className='my-3 border-l-4 border-primary/40 pl-4 italic text-muted-foreground'
      {...props}
    >
      {children}
    </blockquote>
  ),

  a: ({ node, href, children, ...props }: any) => (
    <a
      href={href}
      className='text-primary underline underline-offset-2 transition-opacity hover:opacity-70'
      target='_blank'
      rel='noopener noreferrer'
      {...props}
    >
      {children}
    </a>
  ),

  hr: ({ node, ...props }: any) => (
    <hr className='my-4 border-border' {...props} />
  ),

  strong: ({ node, children, ...props }: any) => (
    <strong className='font-semibold' {...props}>
      {children}
    </strong>
  ),

  table: ({ node, children, ...props }: any) => (
    <div className='my-4 overflow-x-auto rounded-lg border border-border'>
      <table className='w-full border-collapse text-sm' {...props}>
        {children}
      </table>
    </div>
  ),
  thead: ({ node, children, ...props }: any) => (
    <thead className='bg-muted' {...props}>
      {children}
    </thead>
  ),
  th: ({ node, children, ...props }: any) => (
    <th
      className='border-b border-border px-4 py-2.5 text-left font-semibold'
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ node, children, ...props }: any) => (
    <td className='border-b border-border px-4 py-2' {...props}>
      {children}
    </td>
  ),
  tr: ({ node, children, ...props }: any) => (
    <tr className='transition-colors last:[&>td]:border-0 hover:bg-muted/30' {...props}>
      {children}
    </tr>
  ),
}
