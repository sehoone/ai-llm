'use client'

import { useSearchParams } from 'next/navigation'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { AuthLayout } from '../auth-layout'
import { UserAuthForm } from './components/user-auth-form'

export function SignIn() {
  const searchParams = useSearchParams()
  const redirect = searchParams.get('redirect')

  return (
    <AuthLayout>
      <Card className='gap-4'>
        <CardHeader>
          <CardTitle className='text-lg tracking-tight'>관리자 로그인</CardTitle>
        </CardHeader>
        <CardContent>
          <UserAuthForm redirectTo={redirect || undefined} />
        </CardContent>
      </Card>
    </AuthLayout>
  )
}
