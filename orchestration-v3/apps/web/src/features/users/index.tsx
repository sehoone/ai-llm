'use client'

import { ConfigDrawer } from '@/components/config-drawer'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { UsersDialogs } from './components/users-dialogs'
import { UsersPrimaryButtons } from './components/users-primary-buttons'
import { UsersProvider, useUsers } from './components/users-provider'
import { UsersTable } from './components/users-table'

function UsersContent({ title, desc }: { title: string; desc: string }) {
  const { users, isLoading } = useUsers()

  if (isLoading) return <div>Loading...</div>

  return (
    <>
      <Header fixed>
        <Search />
        <div className='ms-auto flex items-center space-x-4'>
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main className='flex flex-1 flex-col gap-4 sm:gap-6'>
        <div className='flex flex-wrap items-end justify-between gap-2'>
          <div>
            <h2 className='text-2xl font-bold tracking-tight'>{title}</h2>
            <p className='text-muted-foreground'>
              {desc}
            </p>
          </div>
          <UsersPrimaryButtons />
        </div>
        <UsersTable data={users} />
      </Main>

      <UsersDialogs />
    </>
  )
}

export function Users() {

  return (
    <UsersProvider>
      <UsersContent title='User List' desc='Manage users.' />
    </UsersProvider>
  )
}
