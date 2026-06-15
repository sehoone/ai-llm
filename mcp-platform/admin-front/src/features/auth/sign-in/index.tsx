'use client'

import { useSearchParams } from 'next/navigation'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { AuthLayout } from '../auth-layout'
import { UserAuthForm } from './components/user-auth-form'

const isKeycloakMode = process.env.NEXT_PUBLIC_AUTH_MODE === 'keycloak'

export function SignIn() {
  const searchParams = useSearchParams()
  const redirect = searchParams.get('redirect')

  return (
    <AuthLayout>
      <Card className='gap-4'>
        <CardHeader>
          <CardTitle className='text-lg tracking-tight'>관리자 로그인</CardTitle>
          {isKeycloakMode && (
            <CardDescription className='text-xs text-muted-foreground'>
              Keycloak 계정으로 로그인합니다.
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <UserAuthForm redirectTo={redirect || undefined} />
        </CardContent>
      </Card>
    </AuthLayout>
  )
}
