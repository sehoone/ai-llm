import { SignUp } from '@clerk/nextjs'
import { Skeleton } from '@/components/ui/skeleton'

export default function SignUpPage() {
  return (
    <SignUp fallback={<Skeleton className='h-[30rem] w-[25rem]' />} />
  )
}
