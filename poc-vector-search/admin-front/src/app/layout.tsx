/* eslint-disable react-refresh/only-export-components */
import '@/styles/index.css'
import { cookies } from 'next/headers'
import { Providers } from './providers'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'AI Admin',
  description: 'Admin dashboard built with Shadcn UI',
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const cookieStore = await cookies()
  const theme = cookieStore.get('vite-ui-theme')?.value
  const font = cookieStore.get('font')?.value
  const dir = cookieStore.get('dir')?.value

  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers initialTheme={theme} initialFont={font} initialDir={dir}>
          {children}
        </Providers>
      </body>
    </html>
  )
}
