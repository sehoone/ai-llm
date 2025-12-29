import { SignIn } from '@clerk/nextjs'
import { Skeleton } from '@/components/ui/skeleton'

export default function SignInPage() {
  return (
    <SignIn
      initialValues={{
        emailAddress: 'your_mail+shadcn_admin@gmail.com',
      }}
      fallback={<Skeleton className='h-[30rem] w-[25rem]' />}
    />
  )
}
