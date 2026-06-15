'use client'

import { useState } from 'react'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth-store'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/password-input'

const formSchema = z.object({
  email: z.email({
    error: (iss) => (iss.input === '' ? 'Please enter your email' : undefined),
  }),
  password: z
    .string()
    .min(1, 'Please enter your password')
    .min(7, 'Password must be at least 7 characters long'),
})

interface UserAuthFormProps extends React.HTMLAttributes<HTMLFormElement> {
  redirectTo?: string
}

export function UserAuthForm({
  className,
  redirectTo,
  ...props
}: UserAuthFormProps) {
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()
  const { auth } = useAuthStore()

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  })

  function onSubmit(data: z.infer<typeof formSchema>) {
    setIsLoading(true)

    toast.promise(login(data), {
      loading: 'Signing in...',
      success: (response) => {
        setIsLoading(false)

        const expiresAt = new Date(Date.now() + response.expiresIn * 1000).toISOString()

        const user = {
          accountNo: 'UNKNOWN',
          email: data.email,
          role: [response.user?.role?.toLowerCase() || 'user'],
          exp: new Date(expiresAt).getTime(),
        }

        auth.setUser(user)
        auth.setAccessToken(response.accessToken)
        auth.setRefreshToken(response.refreshToken)
        auth.setExpiresAt(expiresAt)

        // Redirect to internal path only — prevent open redirect
        const targetPath =
          redirectTo && redirectTo.startsWith('/') && !redirectTo.startsWith('//')
            ? redirectTo
            : '/'
        router.replace(targetPath)

        return `Welcome back, ${data.email}!`
      },
      error: (err) => {
        setIsLoading(false)
        return err.response?.data?.message || 'Error signing in'
      },
    })
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className={cn('grid gap-3', className)}
        {...props}
      >
        <FormField
          control={form.control}
          name='email'
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input placeholder='name@example.com' {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name='password'
          render={({ field }) => (
            <FormItem className='relative'>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <PasswordInput placeholder='********' {...field} />
              </FormControl>
              <FormMessage />
              {/* <Link
                href='/forgot-password'
                className='absolute end-0 -top-0.5 text-sm font-medium text-muted-foreground hover:opacity-75'
              >
                Forgot password?
              </Link> */}
            </FormItem>
          )}
        />
        <Button className='mt-2' disabled={isLoading}>
          {/* {isLoading ? <Loader2 className='animate-spin' /> : <LogIn />} */}
          로그인
        </Button>


      </form>
    </Form>
  )
}
