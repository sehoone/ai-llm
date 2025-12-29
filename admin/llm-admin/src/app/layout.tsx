import '@/styles/index.css'
import { Providers } from './providers'

export const metadata = {
  title: 'Shadcn Admin',
  description: 'Admin dashboard built with Shadcn UI',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
