'use client'

import { ConfigDrawer } from '@/components/config-drawer'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { TabBasicChat } from './components/sample-tabs/tab-01-basic-chat'
import { TabDeepThinking } from './components/sample-tabs/tab-02-deep-thinking'
import { TabLlmService } from './components/sample-tabs/tab-03-llm-service'
import { TabRag } from './components/sample-tabs/tab-04-rag'
import { TabPatterns } from './components/sample-tabs/tab-05-patterns'
import { TabWorkflow } from './components/sample-tabs/tab-06-workflow'
import { TabDatabase } from './components/sample-tabs/tab-07-database'
import { TabObservability } from './components/sample-tabs/tab-08-observability'

const TABS = [
  { value: 'basic-chat',    label: '01 채팅',      Component: TabBasicChat },
  { value: 'deep-thinking', label: '02 딥씽킹',    Component: TabDeepThinking },
  { value: 'llm',           label: '03 LLM',       Component: TabLlmService },
  { value: 'rag',           label: '04 RAG',       Component: TabRag },
  { value: 'patterns',      label: '05 패턴',      Component: TabPatterns },
  { value: 'workflow',      label: '06 워크플로우', Component: TabWorkflow },
  { value: 'db',            label: '07 DB',        Component: TabDatabase },
  { value: 'observability', label: '08 관찰성',    Component: TabObservability },
]

export function Products() {
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
        <div>
          <h2 className='text-2xl font-bold tracking-tight'>Sample API Explorer</h2>
          <p className='text-muted-foreground'>
            <code className='rounded bg-muted px-1 text-xs'>/api/v1/sample/</code> 하위 샘플 엔드포인트 데모
          </p>
        </div>

        <Tabs defaultValue='basic-chat' className='flex-1'>
          <TabsList className='mb-4 flex-wrap h-auto gap-1'>
            {TABS.map(({ value, label }) => (
              <TabsTrigger key={value} value={value} className='text-xs'>
                {label}
              </TabsTrigger>
            ))}
          </TabsList>

          {TABS.map(({ value, Component }) => (
            <TabsContent key={value} value={value} className='overflow-y-auto'>
              <Component />
            </TabsContent>
          ))}
        </Tabs>
      </Main>
    </>
  )
}
