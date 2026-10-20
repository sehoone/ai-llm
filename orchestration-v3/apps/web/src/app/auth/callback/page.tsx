'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { completeLogin } from '@/lib/oidc'
import { logger } from '@/lib/logger'
import { useAuthStore } from '@/stores/auth-store'

// IdP 콜백: code→token 교환 후 세션 저장, 원래 경로로 복귀.
export default function CallbackPage() {
  const router = useRouter()
  const { auth } = useAuthStore()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    completeLogin()
      .then(({ accessToken, idToken, returnTo }) => {
        auth.setSession(accessToken, idToken)
        router.replace(returnTo)
      })
      .catch((err) => {
        logger.error({ err }, 'OIDC 콜백 처리 실패')
        setError('로그인을 완료하지 못했습니다.')
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className='flex min-h-svh items-center justify-center text-muted-foreground'>
      {error ?? '로그인 처리 중…'}
    </div>
  )
}
