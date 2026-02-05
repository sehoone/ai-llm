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
    errMsg = error.response?.data.title || errMsg
  }

  toast.error(errMsg)
}
