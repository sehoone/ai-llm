'use client'

import { useEffect } from 'react'
import { GeneralError } from '@/features/errors/general-error'
import { logger } from '@/lib/logger'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    logger.error('Unhandled page error', { message: error.message, digest: error.digest })
  }, [error])

  return <GeneralError onReset={reset} />
}
