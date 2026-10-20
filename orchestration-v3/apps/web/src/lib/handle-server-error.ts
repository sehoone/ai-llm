import { AxiosError } from 'axios'
import { toast } from 'sonner'
import { logger } from './logger'

export function handleServerError(error: unknown) {
  logger.debug(error)

  let errMsg = 'Something went wrong!'

  if (
    error &&
    typeof error === 'object' &&
    'status' in error &&
    Number(error.status) === 204
  ) {
    errMsg = 'Content not found.'
  }

  if (error instanceof AxiosError) {
    const data = error.response?.data
    const detail = data?.detail
    errMsg = (typeof detail === 'string' ? detail : null) ?? data?.title ?? errMsg
  }

  toast.error(errMsg)
}
