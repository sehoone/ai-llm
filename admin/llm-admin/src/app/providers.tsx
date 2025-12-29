'use client'

import * as React from 'react'
import { Suspense } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { ThemeProvider } from '@/context/theme-provider'
import { FontProvider } from '@/context/font-provider'
import { DirectionProvider } from '@/context/direction-provider'
import { Toaster } from '@/components/ui/sonner'
import { NavigationProgress } from '@/components/navigation-progress'
import { handleServerError } from '@/lib/handle-server-error'
import { toast } from 'sonner'
import { AxiosError } from 'axios'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          if (process.env.NODE_ENV === 'development') console.log({ failureCount, error })
          if (failureCount >= 0 && process.env.NODE_ENV === 'development') return false
          if (failureCount > 3 && process.env.NODE_ENV === 'production') return false
          return !(
            error instanceof AxiosError &&
            [401, 403].includes(error.response?.status ?? 0)
          )
        },
        refetchOnWindowFocus: process.env.NODE_ENV === 'production',
        staleTime: 10 * 1000,
      },
      mutations: {
        onError: (error) => {
          handleServerError(error)
          if (error instanceof AxiosError) {
            if (error.response?.status === 304) {
              toast.error('Content not modified!')
            }
          }
        },
      },
    },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      <DirectionProvider>
        <FontProvider>
          <ThemeProvider defaultTheme='light' storageKey='vite-ui-theme'>
            <Suspense fallback={null}>
              <NavigationProgress />
            </Suspense>
            {children}
            <Toaster />
            <ReactQueryDevtools initialIsOpen={false} />
          </ThemeProvider>
        </FontProvider>
      </DirectionProvider>
    </QueryClientProvider>
  )
}
