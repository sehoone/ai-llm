'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import { ragApi, type RAGSearchResult } from '@/api/rag'
import { DEFAULT_LLM_MODEL, type LlmModel } from '@/config/models'
import { logger } from '@/lib/logger'
import { SearchConfiguration } from './components/search-configuration'
import { SearchInput } from './components/search-input'
import { SearchResults } from './components/search-results'

export default function NaturalSearch() {
  const [loading, setLoading] = useState(false)
  const [searching, setSearching] = useState(false) // State for spinner
  const [summary, setSummary] = useState('')
  const [results, setResults] = useState<RAGSearchResult[]>([])
  const [hasStarted, setHasStarted] = useState(false)
  
  const [ragKey, setRagKey] = useState('')

  const [ragGroup, setRagGroup] = useState('')
  const [ragType, setRagType] = useState<'user_isolated' | 'chatbot_shared' | 'natural_search'>('natural_search')
  const [query, setQuery] = useState('')
  const [model, setModel] = useState<LlmModel>(DEFAULT_LLM_MODEL)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setSearching(true)
    setHasStarted(true)
    setSummary('')
    setResults([])

    try {
        await ragApi.naturalLanguageSearchStream(
            {
                rag_type: ragType,
                query: query,
                rag_key: ragKey,
                rag_group: ragGroup,
                limit: 5,
                model: model
            },
            (json) => {
                if (json.type === 'sources') {
                    setResults(json.data)
                    setSearching(false) // Data started coming
                } else if (json.type === 'chunk') {
                    setSummary(prev => prev + json.data)
                    setSearching(false)
                } else if (json.type === 'error') {
                    toast.error(json.data)
                }
            },
            (error) => {
                logger.error("Stream error", error);
                throw error;
            }
        )

    } catch (error) {
      logger.error(error)
      toast.error('Search failed')
    } finally {
      setLoading(false)
      setSearching(false)
    }
  }

  return (
    <div className='flex flex-col gap-4 p-4 md:p-8'>
      <div className='flex items-center justify-between space-y-2'>
        <h2 className='text-3xl font-bold tracking-tight'>Natural Language Search</h2>
      </div>
      
      <SearchConfiguration
        model={model}
        setModel={setModel}
        ragType={ragType}
        setRagType={setRagType}
        ragKey={ragKey}
        setRagKey={setRagKey}
        ragGroup={ragGroup}
        setRagGroup={setRagGroup}
      />

      <SearchInput
        query={query}
        setQuery={setQuery}
        handleSearch={handleSearch}
        loading={loading}
        searching={searching}
      />

      <SearchResults
        searching={searching}
        hasStarted={hasStarted}
        summary={summary}
        results={results}
      />
    </div>
  )
}
