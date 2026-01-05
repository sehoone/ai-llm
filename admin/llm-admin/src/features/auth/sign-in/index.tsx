'use client'

import { useSearchParams } from 'next/navigation'
import {
  Card,
  CardContent,
  CardDescription,
  // CardFooter,
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
          {/* <CardDescription>
            이메일과 비밀번호를 입력하세요. <br />
            
          </CardDescription> */}
        </CardHeader>
        <CardContent>
          <UserAuthForm redirectTo={redirect || undefined} />
        </CardContent>
        {/* <CardFooter>
          <p className='px-8 text-center text-sm text-muted-foreground'>
            By clicking sign in, you agree to our{' '}
            <a
              href='/terms'
              className='underline underline-offset-4 hover:text-primary'
            >
              Terms of Service
            </a>{' '}
            and{' '}
            <a
              href='/privacy'
              className='underline underline-offset-4 hover:text-primary'
            >
              Privacy Policy
            </a>
            .
          </p>
        </CardFooter> */}
      </Card>
    </AuthLayout>
  )
}
