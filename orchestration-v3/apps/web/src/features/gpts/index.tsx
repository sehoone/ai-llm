'use client'

import { useEffect, useState } from 'react'
import { Plus, Bot, Edit, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { customGptApi, type CustomGPT } from '@/api/custom-gpts'
import { useRouter } from 'next/navigation'
import { Main } from '@/components/layout/main'
import { Header } from '@/components/layout/header'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { ConfigDrawer } from '@/components/config-drawer'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'

export function Gpts() {
  const [gpts, setGpts] = useState<CustomGPT[]>([])
  const router = useRouter()

  useEffect(() => {
    const loadGpts = async () => {
      try {
        const data = await customGptApi.getAll()
        setGpts(data)
      } catch (error) {
        logger.error('Failed to load GPTs', error)
        toast.error('Failed to load GPTs')
      }
    }
    loadGpts()
  }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this GPT?')) return
    try {
      await customGptApi.delete(id)
      setGpts(gpts.filter((g) => g.id !== id))
      toast.success('GPT deleted successfully')
    } catch (error) {
       logger.error('Failed to delete GPT', error)
       toast.error('Failed to delete GPT')
    }
  }

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

      <Main>
        <div className='flex items-center justify-between mb-6'>
          <div>
            <h2 className='text-2xl font-bold tracking-tight'>My GPTs</h2>
            <p className='text-muted-foreground'>
              Create and manage your custom GPTs.
            </p>
          </div>
          <Button onClick={() => router.push('/gpts/create')}>
            <Plus className='mr-2 h-4 w-4' /> Create new GPT
          </Button>
        </div>

        <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3'>
          {gpts.map((gpt) => (
            <Card key={gpt.id} className='flex flex-col'>
              <CardHeader>
                <div className='flex items-center gap-2'>
                  <div className='p-2 bg-primary/10 rounded-full'>
                    <Bot className='h-6 w-6 text-primary' />
                  </div>
                  <CardTitle className='text-xl'>{gpt.name}</CardTitle>
                </div>
                <CardDescription>{gpt.description || 'No description'}</CardDescription>
              </CardHeader>
              <CardContent className='flex-1'>
                 {/* Provide some content or stats here if available */}
                 <p className='text-sm text-muted-foreground line-clamp-3'>
                    {gpt.instructions}
                 </p>
              </CardContent>
              <CardFooter className='flex justify-end gap-2'>
                <Button variant='ghost' size='sm' onClick={() => router.push(`/gpts/${gpt.id}`)}>
                  <Edit className='h-4 w-4 mr-1' /> Edit
                </Button>
                <Button variant='ghost' size='sm' className="text-destructive hover:text-destructive" onClick={() => handleDelete(gpt.id)}>
                  <Trash2 className='h-4 w-4 mr-1' /> Delete
                </Button>
                 <Button size='sm' onClick={() => router.push(`/gpts/${gpt.id}/chat`)}>
                  Chat
                </Button>
              </CardFooter>
            </Card>
          ))}
          {gpts.length === 0 && (
             <div className="col-span-full text-center py-12 text-muted-foreground">
                No GPTs found. Create one to get started.
             </div>
          )}
        </div>
      </Main>
    </>
  )
}
