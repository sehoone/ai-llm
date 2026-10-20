'use client'

import { useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { beginLogin } from '@/lib/oidc'
import { logger } from '@/lib/logger'

// ADR-0003: 자체 로그인 화면 없음. 진입 즉시 사내 IdP authorize로 리다이렉트.
export default function LoginPage() {
  const searchParams = useSearchParams()

  useEffect(() => {
    const returnTo = searchParams.get('redirect') || '/'
    beginLogin(returnTo).catch((err) => logger.error({ err }, 'IdP 로그인 리다이렉트 실패'))
  }, [searchParams])

  return (
    <div className='flex min-h-svh items-center justify-center text-muted-foreground'>
      사내 인증으로 이동 중…
    </div>
  )
}
