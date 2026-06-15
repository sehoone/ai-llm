import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'
import { type Collapsible, type Variant } from '@/context/layout-provider'

export default async function Layout({
  children,
}: {
  children: React.ReactNode
}) {
  const cookieStore = await cookies()

  const token = cookieStore.get('access_token')
  if (!token) {
    redirect('/sign-in')
  }

  const defaultOpen = cookieStore.get('sidebar_state')?.value !== 'false'
  const defaultCollapsible =
    (cookieStore.get('layout_collapsible')?.value as Collapsible) || 'icon'
  const defaultVariant =
    (cookieStore.get('layout_variant')?.value as Variant) || 'inset'

  return (
    <AuthenticatedLayout
      defaultOpen={defaultOpen}
      defaultCollapsible={defaultCollapsible}
      defaultVariant={defaultVariant}
    >
      {children}
    </AuthenticatedLayout>
  )
}
