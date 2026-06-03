'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import * as api from '@/api/sample'
import { Section, JsonResult } from '../section'

const LOG_LEVELS = ['debug', 'info', 'warning', 'error'] as const
const MODELS = ['gpt-4o', 'gpt-4o-mini', 'gpt-5', 'gpt-5-mini']

export function TabObservability() {
  const [logLevel, setLogLevel] = useState<string>('info')
  const [logResult, setLogResult] = useState<unknown>(null)

  const [operation, setOperation] = useState('')
  const [bizResult, setBizResult] = useState<unknown>(null)
  const [bizLoading, setBizLoading] = useState(false)

  const [contextResult, setContextResult] = useState<unknown>(null)

  const [metricsModel, setMetricsModel] = useState('gpt-4o')
  const [metricsResult, setMetricsResult] = useState<unknown>(null)

  const handleBizOp = async () => {
    if (!operation.trim()) return
    setBizLoading(true)
    try { setBizResult(await api.businessOp({ operation })) }
    finally { setBizLoading(false) }
  }

  return (
    <div className='space-y-4'>
      <Section title='structlog 레벨별 사용법' endpoint='/api/v1/sample/observability/log-demo'>
        <p className='mb-2 text-xs text-muted-foreground'>
          규칙: logger.info("이벤트명", key=value) — f-string 절대 금지
        </p>
        <div className='flex gap-2'>
          <div className='flex gap-1'>
            {LOG_LEVELS.map((l) => (
              <Button
                key={l}
                size='sm'
                variant={logLevel === l ? 'default' : 'outline'}
                onClick={() => setLogLevel(l)}
              >
                {l}
              </Button>
            ))}
          </div>
          <Button size='sm' onClick={async () => setLogResult(await api.getLogDemo(logLevel))}>실행</Button>
        </div>
        <JsonResult data={logResult} />
      </Section>

      <Section title='서비스 레이어 로깅 패턴' endpoint='/api/v1/sample/observability/business-op' method='POST'>
        <p className='mb-2 text-xs text-muted-foreground'>
          시작/완료/실패 이벤트 쌍 + 타이밍 측정 패턴
        </p>
        <div className='flex gap-2'>
          <Input
            value={operation}
            onChange={(e) => setOperation(e.target.value)}
            placeholder='operation 이름 (예: user_signup, doc_upload)'
            disabled={bizLoading}
            className='flex-1'
          />
          <Button size='sm' onClick={handleBizOp} disabled={bizLoading || !operation.trim()}>
            {bizLoading ? '실행 중…' : '실행'}
          </Button>
        </div>
        <JsonResult data={bizResult} />
      </Section>

      <Section title='미들웨어 자동 바인딩 컨텍스트' endpoint='/api/v1/sample/observability/context'>
        <p className='mb-2 text-xs text-muted-foreground'>
          LoggingContextMiddleware가 모든 요청에 request_id / user_id를 자동 바인딩합니다.
        </p>
        <Button size='sm' onClick={async () => setContextResult(await api.getObservabilityContext())}>조회</Button>
        <JsonResult data={contextResult} />
      </Section>

      <Section title='Prometheus 지표 수동 기록' endpoint='/api/v1/sample/observability/metrics-demo'>
        <p className='mb-2 text-xs text-muted-foreground'>
          llm_inference_duration_seconds Histogram에 시뮬레이션 값을 기록합니다.
        </p>
        <div className='flex gap-2'>
          <div className='flex gap-1'>
            {MODELS.map((m) => (
              <Button
                key={m}
                size='sm'
                variant={metricsModel === m ? 'default' : 'outline'}
                onClick={() => setMetricsModel(m)}
              >
                {m}
              </Button>
            ))}
          </div>
          <Button size='sm' onClick={async () => setMetricsResult(await api.getMetricsDemo(metricsModel))}>
            기록
          </Button>
        </div>
        <JsonResult data={metricsResult} />
      </Section>
    </div>
  )
}
