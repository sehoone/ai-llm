'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { customGptApi, type CreateCustomGPTData } from '@/api/custom-gpts'
import { GptForm } from './components/gpt-form'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { ConfigDrawer } from '@/components/config-drawer'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { RagDocuments } from './components/rag-documents'

export function CreateGpt() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  // Generate a random RAG key for the new GPT so documents can be uploaded before creation
  const [ragKey] = useState(() => `gpt_${crypto.randomUUID().replace(/-/g, '')}`)

  const handleSubmit = async (data: CreateCustomGPTData) => {
    setIsLoading(true)
    try {
      await customGptApi.create({
        ...data,
        rag_key: ragKey,
      })
      toast.success('GPT created successfully')
      router.push('/gpts')
    } catch (error) {
      logger.error('Failed to create GPT', error)
      toast.error('Failed to create GPT')
    } finally {
      setIsLoading(false)
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
        <div className='mb-6'>
          <h2 className='text-2xl font-bold tracking-tight'>Create New GPT</h2>
          <p className='text-muted-foreground'>
            Configure a new custom GPT assistant.
          </p>
        </div>

        <div className='max-w-4xl space-y-8'>
            <div className='grid gap-8 lg:grid-cols-2'>
                <div>
                     <h3 className='text-lg font-medium mb-4'>Configuration</h3>
                    <GptForm onSubmit={handleSubmit} isLoading={isLoading} />
                </div>
                
                <div className='space-y-6'>
                    <div>
                        <h3 className='text-lg font-medium mb-4'>Knowledge Base</h3>
                        <p className='text-sm text-muted-foreground mb-4'>
                            Documents uploaded here will be used by this GPT to answer questions.
                        </p>
                        <RagDocuments ragKey={ragKey} ragType="chatbot_shared" />
                    </div>
                </div>
            </div>
        </div>
      </Main>
    </>
  )
}
