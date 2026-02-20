'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { customGptApi, type CustomGPT, type UpdateCustomGPTData } from '@/api/custom-gpts'
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

export function EditGpt() {
  const params = useParams()
  const gptId = params.gptId as string
  const router = useRouter()
  const [gpt, setGpt] = useState<CustomGPT | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    const loadGpt = async () => {
      if (!gptId) return
      setIsLoading(true)
      try {
        const data = await customGptApi.get(gptId)
        setGpt(data)
      } catch (error) {
        logger.error('Failed to load GPT', error)
        toast.error('Failed to load GPT details')
        router.push('/gpts')
      } finally {
        setIsLoading(false)
      }
    }
    loadGpt()
  }, [gptId, router])

  const handleSubmit = async (data: UpdateCustomGPTData) => {
    if (!gptId) return
    setIsSaving(true)
    try {
      const updatedGpt = await customGptApi.update(gptId, data)
      setGpt(updatedGpt)
      toast.success('GPT updated successfully')
    } catch (error) {
      logger.error('Failed to update GPT', error)
      toast.error('Failed to update GPT')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) return <div>Loading...</div>
  if (!gpt) return <div>GPT not found</div>

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
          <h2 className='text-2xl font-bold tracking-tight'>Edit GPT</h2>
          <p className='text-muted-foreground'>
            Update your custom GPT configuration.
          </p>
        </div>

        <div className='max-w-4xl space-y-8'>
            <div className='grid gap-8 lg:grid-cols-2'>
                <div>
                     <h3 className='text-lg font-medium mb-4'>Configuration</h3>
                    <GptForm initialData={gpt} onSubmit={handleSubmit} isLoading={isSaving} />
                </div>
                
                <div className='space-y-6'>
                    <div>
                        <h3 className='text-lg font-medium mb-4'>Knowledge Base</h3>
                        <p className='text-sm text-muted-foreground mb-4'>
                            Documents uploaded here will be used by this GPT to answer questions.
                        </p>
                        <RagDocuments ragKey={gpt.rag_key} ragType="chatbot_shared" />
                    </div>
                </div>
            </div>
        </div>
      </Main>
    </>
  )
}
