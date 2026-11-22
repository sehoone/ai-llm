'use client'

import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import * as api from '@/api/sample'
import { Section, JsonResult, ErrorMsg } from '../section'

export function TabRag() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploadResult, setUploadResult] = useState<unknown>(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const [query, setQuery] = useState('')
  const [searchResult, setSearchResult] = useState<unknown>(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  const [question, setQuestion] = useState('')
  const [askResult, setAskResult] = useState<api.AskResponse | null>(null)
  const [askLoading, setAskLoading] = useState(false)
  const [askError, setAskError] = useState<string | null>(null)

  const [deleteResult, setDeleteResult] = useState<unknown>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0]
    if (!file) return
    setUploadLoading(true); setUploadError(null)
    try { setUploadResult(await api.uploadRagDocument(file)) }
    catch (e: unknown) { setUploadError(e instanceof Error ? e.message : '업로드 오류') }
    finally { setUploadLoading(false) }
  }

  const handleSearch = async () => {
    if (!query.trim()) return
    setSearchLoading(true); setSearchError(null)
    try { setSearchResult(await api.searchRag({ query })) }
    catch (e: unknown) { setSearchError(e instanceof Error ? e.message : '검색 오류') }
    finally { setSearchLoading(false) }
  }

  const handleAsk = async () => {
    if (!question.trim()) return
    setAskLoading(true); setAskError(null)
    try { setAskResult(await api.askRag({ question })) }
    catch (e: unknown) { setAskError(e instanceof Error ? e.message : 'Q&A 오류') }
    finally { setAskLoading(false) }
  }

  const handleDelete = async () => {
    setDeleteLoading(true)
    try { setDeleteResult(await api.deleteRagDocs()) }
    finally { setDeleteLoading(false) }
  }

  return (
    <div className='space-y-4'>
      <Section title='문서 업로드' endpoint='/api/v1/sample/rag/upload' method='POST'>
        <p className='mb-2 text-xs text-muted-foreground'>
          .txt, .md, .json, .csv 파일 → 500자 청킹 → text-embedding-3-small → pgvector 저장
        </p>
        <div className='flex gap-2'>
          <input ref={fileRef} type='file' accept='.txt,.md,.json,.csv' className='flex-1 text-sm' />
          <Button size='sm' onClick={handleUpload} disabled={uploadLoading}>
            {uploadLoading ? '업로드 중…' : '업로드'}
          </Button>
        </div>
        <JsonResult data={uploadResult} />
        <ErrorMsg error={uploadError} />
      </Section>

      <Section title='유사도 검색' endpoint='/api/v1/sample/rag/search' method='POST'>
        <p className='mb-2 text-xs text-muted-foreground'>
          pgvector cosine similarity로 가장 유사한 청크를 검색합니다.
        </p>
        <div className='flex gap-2'>
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='검색할 내용을 입력하세요'
            disabled={searchLoading}
            className='flex-1'
          />
          <Button size='sm' onClick={handleSearch} disabled={searchLoading || !query.trim()}>
            {searchLoading ? '검색 중…' : '검색'}
          </Button>
        </div>
        <JsonResult data={searchResult} />
        <ErrorMsg error={searchError} />
      </Section>

      <Section title='RAG 기반 Q&A' endpoint='/api/v1/sample/rag/ask' method='POST'>
        <p className='mb-2 text-xs text-muted-foreground'>
          검색 청크를 system_prompt에 주입 → LangGraphAgent 호출
        </p>
        <div className='flex gap-2'>
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder='업로드한 문서 기반으로 질문하세요'
            disabled={askLoading}
            className='flex-1'
          />
          <Button size='sm' onClick={handleAsk} disabled={askLoading || !question.trim()}>
            {askLoading ? '답변 중…' : '질문'}
          </Button>
        </div>
        {askResult && (
          <div className='mt-2 space-y-1'>
            <p className='rounded-md bg-muted p-3 text-sm whitespace-pre-wrap'>{askResult.answer}</p>
            <p className='text-xs text-muted-foreground'>
              참조 청크: {askResult.retrieved_chunks}개 | session: {askResult.session_id.slice(0, 8)}…
            </p>
          </div>
        )}
        <ErrorMsg error={askError} />
      </Section>

      <Section title='샘플 문서 삭제' endpoint='/api/v1/sample/rag/docs' method='DELETE'>
        <p className='mb-2 text-xs text-muted-foreground'>rag_key=sample-demo 의 임베딩을 모두 삭제합니다.</p>
        <Button size='sm' variant='destructive' onClick={handleDelete} disabled={deleteLoading}>
          {deleteLoading ? '삭제 중…' : '삭제'}
        </Button>
        <JsonResult data={deleteResult} />
      </Section>
    </div>
  )
}
