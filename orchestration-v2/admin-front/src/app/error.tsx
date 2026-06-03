'use client'

import { useEffect } from 'react'
import { GeneralError } from '@/features/errors/general-error'
import { logger } from '@/lib/logger'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    logger.error('Unhandled global error', { message: error.message, digest: error.digest })
  }, [error])

  return (
    <html>
      <body>
        <GeneralError onReset={reset} />
      </body>
    </html>
  )
}
