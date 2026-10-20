'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import * as api from '@/api/sample'
import { Section, JsonResult, ErrorMsg } from '../section'

type Preset = { name: string; description: string; nodes: api.NodeDef[] }

export function TabWorkflow() {
  const [nodeTypes, setNodeTypes] = useState<unknown>(null)
  const [presets, setPresets] = useState<Record<string, Preset> | null>(null)
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null)

  const [runResult, setRunResult] = useState<unknown>(null)
  const [runLoading, setRunLoading] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  const [streamLog, setStreamLog] = useState<{ event: string; data: string }[]>([])
  const [streamLoading, setStreamLoading] = useState(false)

  const handleLoadPresets = async () => {
    const res = await api.getWorkflowPresets()
    setPresets(res.presets)
    if (!selectedPreset && res.presets) {
      setSelectedPreset(Object.keys(res.presets)[0])
    }
  }

  const getSelectedNodes = (): api.NodeDef[] => {
    if (!presets || !selectedPreset) return []
    return presets[selectedPreset]?.nodes ?? []
  }

  const handleRun = async () => {
    const nodes = getSelectedNodes()
    if (!nodes.length) return
    setRunLoading(true); setRunError(null); setRunResult(null)
    try {
      setRunResult(await api.runWorkflow({ name: selectedPreset ?? '워크플로우', nodes }))
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : '실행 오류')
    } finally {
      setRunLoading(false)
    }
  }

  const handleStream = async () => {
    const nodes = getSelectedNodes()
    if (!nodes.length) return
    setStreamLoading(true); setStreamLog([])
    try {
      await api.streamWorkflow(
        { name: selectedPreset ?? '워크플로우', nodes },
        {
          onToken: () => {},
          onEvent: (event, data) => {
            setStreamLog((prev) => [...prev, { event, data }])
          },
        },
      )
    } finally {
      setStreamLoading(false)
    }
  }

  return (
    <div className='space-y-4'>
      <Section title='노드 타입 목록' endpoint='/api/v1/sample/workflow/node-types'>
        <Button size='sm' onClick={async () => setNodeTypes(await api.getNodeTypes())}>조회</Button>
        <JsonResult data={nodeTypes} />
      </Section>

      <Section title='프리셋 & 실행' endpoint='/api/v1/sample/workflow/' method='GET | POST'>
        <p className='mb-2 text-xs text-muted-foreground'>
          DAG 의존성 기반 병렬 실행 (asyncio.gather). SSE로 노드별 이벤트 수신 가능.
        </p>

        <div className='mb-3 flex flex-wrap gap-2'>
          <Button size='sm' variant='outline' onClick={handleLoadPresets}>프리셋 로드</Button>
          {presets && Object.keys(presets).map((key) => (
            <Button
              key={key}
              size='sm'
              variant={selectedPreset === key ? 'default' : 'outline'}
              onClick={() => setSelectedPreset(key)}
            >
              {presets[key].name}
            </Button>
          ))}
        </div>

        {selectedPreset && presets?.[selectedPreset] && (
          <p className='mb-2 text-xs text-muted-foreground'>{presets[selectedPreset].description}</p>
        )}

        <div className='flex gap-2'>
          <Button size='sm' onClick={handleRun} disabled={runLoading || !selectedPreset}>
            {runLoading ? '실행 중…' : '실행 (동기)'}
          </Button>
          <Button size='sm' variant='outline' onClick={handleStream} disabled={streamLoading || !selectedPreset}>
            {streamLoading ? '스트리밍 중…' : '실행 (SSE)'}
          </Button>
        </div>

        <JsonResult data={runResult} />
        <ErrorMsg error={runError} />

        {streamLog.length > 0 && (
          <div className='mt-2 space-y-1'>
            <p className='text-xs font-medium'>SSE 이벤트 로그</p>
            <div className='max-h-48 overflow-auto rounded-md bg-muted p-3 space-y-1'>
              {streamLog.map((log, i) => (
                <div key={i} className='flex items-start gap-2 text-xs'>
                  <Badge variant='outline' className='shrink-0 text-xs'>{log.event}</Badge>
                  <span className='font-mono'>{log.data}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Section>
    </div>
  )
}
