import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'

export default function AuthenticatedClerkLayout({ children }: { children: React.ReactNode }) {
  return <AuthenticatedLayout>{children}</AuthenticatedLayout>
}
