'use client'

import { useRouter } from 'next/navigation'
import { buildLogoutUrl } from '@/lib/oidc'
import { useAuthStore } from '@/stores/auth-store'
import { ConfirmDialog } from '@/components/confirm-dialog'

interface SignOutDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SignOutDialog({ open, onOpenChange }: SignOutDialogProps) {
  const router = useRouter()
  const { auth } = useAuthStore()

  const handleSignOut = async () => {
    const idToken = auth.idToken
    auth.reset()
    // IdP 세션 종료 지원 시 그쪽으로, 아니면 로컬 로그아웃 후 /login
    const logoutUrl = await buildLogoutUrl(idToken)
    if (logoutUrl) {
      window.location.href = logoutUrl
    } else {
      router.replace('/login')
    }
  }

  return (
    <ConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      title='Sign out'
      desc='Are you sure you want to sign out? You will need to sign in again to access your account.'
      confirmText='Sign out'
      destructive
      handleConfirm={handleSignOut}
      className='sm:max-w-sm'
    />
  )
}
