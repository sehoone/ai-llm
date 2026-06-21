import { useQuery } from '@tanstack/react-query'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ConfigDrawer } from '@/components/config-drawer'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { TopNav } from '@/components/layout/top-nav'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { ThemeSwitch } from '@/components/theme-switch'
import { getStats } from '@/api/stats'
import { getApiKeys } from '@/api/api-keys'
import { Analytics } from './components/analytics'
import { format } from 'date-fns'
import { Users, Key, UserCheck, KeyRound } from 'lucide-react'

export function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
  })

  const { data: recentKeys = [], isLoading: keysLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: getApiKeys,
  })

  const topRecentKeys = recentKeys.slice(0, 5)

  return (
    <>
      <Header>
        <TopNav links={topNav} />
        <div className='ms-auto flex items-center space-x-4'>
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main>
        <div className='mb-2 flex items-center justify-between space-y-2'>
          <h1 className='text-2xl font-bold tracking-tight'>Dashboard</h1>
        </div>
        <Tabs orientation='vertical' defaultValue='overview' className='space-y-4'>
          <div className='w-full overflow-x-auto pb-2'>
            <TabsList>
              <TabsTrigger value='overview'>Overview</TabsTrigger>
              <TabsTrigger value='analytics'>Analytics</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value='overview' className='space-y-4'>
            {/* Stats cards */}
            <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
              <StatCard
                title='Total Users'
                value={stats?.totalUsers}
                icon={<Users className='h-4 w-4 text-muted-foreground' />}
                isLoading={statsLoading}
              />
              <StatCard
                title='Active Users'
                value={stats?.activeUsers}
                icon={<UserCheck className='h-4 w-4 text-muted-foreground' />}
                isLoading={statsLoading}
              />
              <StatCard
                title='Total API Keys'
                value={stats?.totalApiKeys}
                icon={<Key className='h-4 w-4 text-muted-foreground' />}
                isLoading={statsLoading}
              />
              <StatCard
                title='Active API Keys'
                value={stats?.activeApiKeys}
                icon={<KeyRound className='h-4 w-4 text-muted-foreground' />}
                isLoading={statsLoading}
              />
            </div>

            {/* Recent API Keys */}
            <Card>
              <CardHeader>
                <CardTitle>Recent API Keys</CardTitle>
                <CardDescription>
                  Your most recently issued API keys
                </CardDescription>
              </CardHeader>
              <CardContent>
                {keysLoading ? (
                  <div className='space-y-2'>
                    {[...Array(3)].map((_, i) => (
                      <Skeleton key={i} className='h-10 w-full' />
                    ))}
                  </div>
                ) : topRecentKeys.length === 0 ? (
                  <p className='text-sm text-muted-foreground'>
                    No API keys yet.
                  </p>
                ) : (
                  <div className='space-y-3'>
                    {topRecentKeys.map((key) => (
                      <div
                        key={key.id}
                        className='flex items-center justify-between border-b pb-2 last:border-0 last:pb-0'
                      >
                        <div>
                          <p className='text-sm font-medium'>{key.name}</p>
                          <p className='font-mono text-xs text-muted-foreground'>
                            {key.key}
                          </p>
                        </div>
                        <div className='text-right'>
                          <p className='text-xs text-muted-foreground'>
                            {format(new Date(key.createdAt), 'MMM d, yyyy')}
                          </p>
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
                              key.isActive
                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
                                : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
                            }`}
                          >
                            {key.isActive ? 'Active' : 'Revoked'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value='analytics' className='space-y-4'>
            <Analytics />
          </TabsContent>
        </Tabs>
      </Main>
    </>
  )
}

function StatCard({
  title,
  value,
  icon,
  isLoading,
}: {
  title: string
  value?: number
  icon: React.ReactNode
  isLoading: boolean
}) {
  return (
    <Card>
      <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
        <CardTitle className='text-sm font-medium'>{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className='h-8 w-16' />
        ) : (
          <div className='text-2xl font-bold'>{value ?? 0}</div>
        )}
      </CardContent>
    </Card>
  )
}

const topNav = [
  {
    title: 'Overview',
    href: 'dashboard/overview',
    isActive: true,
    disabled: false,
  },
  {
    title: 'Analytics',
    href: 'dashboard/analytics',
    isActive: false,
    disabled: true,
  },
]
