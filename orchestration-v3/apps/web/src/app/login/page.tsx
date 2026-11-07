'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import axios from 'axios'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PasswordInput } from '@/components/password-input'
import { logger } from '@/lib/logger'
import { useAuthStore } from '@/stores/auth-store'

// 백엔드가 ID/PW를 검증하고 JWT(HS256)를 발급 (ADR-0003 전환, 자체 로그인).
// 인터셉터의 전역 401 처리를 피하려고 로그인 요청은 기본 axios로 직접 호출한다.
const LOGIN_URL = `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/auth/login`

export default function LoginPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { auth } = useAuthStore()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await axios.post(LOGIN_URL, { username, password })
      // ApiResponse<T> 래퍼 → data 언랩 (기본 axios라 수동)
      const data = res.data?.data ?? res.data
      auth.setSession(data.access_token)
      const returnTo = searchParams.get('redirect') || '/'
      router.replace(returnTo)
    } catch (err) {
      logger.error({ err }, '로그인 실패')
      setError('아이디 또는 비밀번호가 올바르지 않습니다.')
      setLoading(false)
    }
  }

  return (
    <div className='flex min-h-svh items-center justify-center p-4'>
      <form
        onSubmit={onSubmit}
        className='w-full max-w-sm space-y-6 rounded-lg border bg-card p-8 shadow-sm'
      >
        <div className='space-y-1 text-center'>
          <h1 className='text-xl font-semibold'>로그인</h1>
          <p className='text-sm text-muted-foreground'>
            계정 정보로 로그인하세요.
          </p>
        </div>

        <div className='space-y-2'>
          <Label htmlFor='username'>아이디</Label>
          <Input
            id='username'
            autoComplete='username'
            autoFocus
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
            required
          />
        </div>

        <div className='space-y-2'>
          <Label htmlFor='password'>비밀번호</Label>
          <PasswordInput
            id='password'
            autoComplete='current-password'
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            required
          />
        </div>

        {error && <p className='text-sm text-destructive'>{error}</p>}

        <Button type='submit' className='w-full' disabled={loading}>
          {loading ? '로그인 중…' : '로그인'}
        </Button>
      </form>
    </div>
  )
}
