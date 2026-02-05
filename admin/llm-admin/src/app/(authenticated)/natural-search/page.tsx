/* eslint-disable @typescript-eslint/no-explicit-any */
'use client'

import { useState } from 'react'
import { Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { ragApi, type RAGSearchResult } from '@/api/rag'
import { toast } from 'sonner'
import { DEFAULT_LLM_MODEL, LLM_MODELS, type LlmModel } from '@/config/models'
import { logger } from '@/lib/logger'

export default function NaturalSearchPage() {
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
      
      <Card>
        <CardHeader>
          <CardTitle>Search Configuration</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
            <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">Model</label>
                <select 
                    className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    value={model} 
                    onChange={(e) => setModel(e.target.value as LlmModel)}
                >
                    {LLM_MODELS.map(m => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                </select>
            </div>
            <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">RAG Type</label>
                <select 
                    className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    value={ragType} 
                    onChange={(e) => setRagType(e.target.value as any)}
                >
                    <option value="natural_search">Natural Search</option>
                    <option value="user_isolated">User Isolated</option>
                    <option value="chatbot_shared">Chatbot Shared</option>
                    
                </select>
            </div>
            <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">RAG Key</label>
                <Input value={ragKey} onChange={e => setRagKey(e.target.value)} placeholder="ex. default" />
            </div>
             <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">RAG Group</label>
                <Input value={ragGroup} onChange={e => setRagGroup(e.target.value)} placeholder="Optional" />
            </div>
        </CardContent>
      </Card>

      <div className="relative">
        <form onSubmit={handleSearch} className="flex w-full items-center space-x-2">
            <Input 
                className="flex-1 text-lg h-12" 
                placeholder="Ask anything..." 
                value={query}
                onChange={e => setQuery(e.target.value)}
            />
            <Button type="submit" size="lg" disabled={loading} className="h-12 w-24">
                {searching ? 'Search...' : <Search className="h-5 w-5" />}
            </Button>
        </form>
      </div>

      {searching && (
        <div className="space-y-4 pt-4">
             <div className="space-y-2">
                <Skeleton className="h-4 w-[250px]" />
                <Skeleton className="h-4 w-[200px]" />
             </div>
             <Skeleton className="h-[125px] w-full rounded-xl" />
        </div>
      )}

      {hasStarted && !searching && (
        <div className="grid gap-6 md:grid-cols-3 pt-4">
            {/* Main Result Area */}
            <div className="md:col-span-2 space-y-6">
                <Card className="bg-muted/50 border-primary/20">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                             ✨ AI Summary
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="leading-relaxed whitespace-pre-wrap">{summary}</p>
                    </CardContent>
                </Card>
            </div>

            {/* Source Documents Area */}
            <div className="space-y-4">
                <h3 className="font-semibold text-lg">Sources</h3>
                {results.map((result, idx) => (
                    <Card key={idx} className="overflow-hidden">
                        <CardHeader className="p-4 pb-2">
                            <CardTitle className="text-sm font-medium truncate" title={result.filename}>
                                {result.filename || `Document ${result.doc_id}`}
                            </CardTitle>
                             <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <Badge variant="secondary" className="text-xs">{Math.round(result.similarity * 100)}% Match</Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-4 pt-2">
                            <p className="text-xs text-muted-foreground line-clamp-3">
                                {result.content}
                            </p>
                        </CardContent>
                    </Card>
                ))}
                 {results.length === 0 && (
                    <p className="text-sm text-muted-foreground">No sources found.</p>
                )}
            </div>
        </div>
      )}
    </div>
  )
}
