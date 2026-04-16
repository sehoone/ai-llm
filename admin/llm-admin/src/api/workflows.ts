/* eslint-disable @typescript-eslint/no-explicit-any */
import api from './axios'
import { useAuthStore } from '@/stores/auth-store'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface WorkflowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: Record<string, any>
}

export interface WorkflowEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

export interface Workflow {
  id: string
  user_id: number
  name: string
  description: string
  definition: WorkflowDefinition
  is_published: boolean
  webhook_token: string | null
  created_at: string
  updated_at: string
}

export interface WorkflowListItem {
  id: string
  user_id: number
  name: string
  description: string
  is_published: boolean
  created_at: string
  updated_at: string
}

export interface NodeExecution {
  id: string
  execution_id: string
  node_id: string
  node_type: string
  status: ExecutionStatus
  input_data: Record<string, any>
  output_data: Record<string, any> | null
  error: string | null
  created_at: string
  completed_at: string | null
}

export interface WorkflowExecution {
  id: string
  workflow_id: string
  user_id: number
  status: ExecutionStatus
  input_data: Record<string, any>
  output_data: Record<string, any> | null
  error: string | null
  created_at: string
  completed_at: string | null
  node_executions: NodeExecution[]
}

export interface ExecutionListItem {
  id: string
  workflow_id: string
  status: ExecutionStatus
  created_at: string
  completed_at: string | null
}

export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped'

export interface WorkflowSchedule {
  id: string
  workflow_id: string
  label: string
  cron_expr: string
  input_data: Record<string, any>
  is_active: boolean
  created_at: string
  next_run_at: string | null
}

export interface NodeType {
  type: string
  input_schema: Record<string, any>
  output_schema: Record<string, any>
}

// ── SSE Event Types ───────────────────────────────────────────────────────────

export type SSEEvent =
  | { type: 'node_start'; node_id: string; node_type: string; input_data: Record<string, any> }
  | { type: 'node_complete'; node_id: string; node_type: string; output_data: Record<string, any> }
  | { type: 'node_failed'; node_id: string; node_type: string; error: string }
  | { type: 'node_skipped'; node_id: string }
  | { type: 'execution_complete'; execution_id: string; output_data: Record<string, any> }
  | { type: 'execution_failed'; execution_id: string; error: string }

// ── API Service ───────────────────────────────────────────────────────────────

export const workflowApi = {
  // Workflow CRUD
  list: async (limit = 50, offset = 0): Promise<WorkflowListItem[]> => {
    const res = await api.get('/api/v1/workflows', { params: { limit, offset } })
    return res.data
  },

  get: async (id: string): Promise<Workflow> => {
    const res = await api.get(`/api/v1/workflows/${id}`)
    return res.data
  },

  create: async (data: { name: string; description?: string; definition?: WorkflowDefinition }): Promise<Workflow> => {
    const res = await api.post('/api/v1/workflows', data)
    return res.data
  },

  update: async (
    id: string,
    data: { name?: string; description?: string; definition?: WorkflowDefinition; is_published?: boolean }
  ): Promise<Workflow> => {
    const res = await api.put(`/api/v1/workflows/${id}`, data)
    return res.data
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/workflows/${id}`)
  },

  togglePublish: async (id: string): Promise<Workflow> => {
    const res = await api.patch(`/api/v1/workflows/${id}/publish`)
    return res.data
  },

  // Node types palette
  getNodeTypes: async (): Promise<NodeType[]> => {
    const res = await api.get('/api/v1/workflows/node-types')
    return res.data
  },

  // Executions
  run: async (workflowId: string, inputData: Record<string, any>): Promise<WorkflowExecution> => {
    const res = await api.post(`/api/v1/workflows/${workflowId}/executions`, { input_data: inputData })
    return res.data
  },

  listExecutions: async (workflowId: string): Promise<ExecutionListItem[]> => {
    const res = await api.get(`/api/v1/workflows/${workflowId}/executions`)
    return res.data
  },

  getExecution: async (executionId: string): Promise<WorkflowExecution> => {
    const res = await api.get(`/api/v1/workflows/executions/${executionId}`)
    return res.data
  },

  // Webhook management
  manageWebhook: async (workflowId: string, action: 'generate' | 'revoke'): Promise<{ webhook_token: string | null }> => {
    const res = await api.patch(`/api/v1/workflows/${workflowId}/webhook`, null, { params: { action } })
    return res.data
  },

  // Schedule CRUD
  listSchedules: async (workflowId: string): Promise<WorkflowSchedule[]> => {
    const res = await api.get(`/api/v1/workflows/${workflowId}/schedules`)
    return res.data
  },

  createSchedule: async (
    workflowId: string,
    data: { label?: string; cron_expr: string; input_data?: Record<string, any> }
  ): Promise<WorkflowSchedule> => {
    const res = await api.post(`/api/v1/workflows/${workflowId}/schedules`, data)
    return res.data
  },

  updateSchedule: async (
    workflowId: string,
    scheduleId: string,
    data: Partial<{ label: string; cron_expr: string; input_data: Record<string, any>; is_active: boolean }>
  ): Promise<WorkflowSchedule> => {
    const res = await api.patch(`/api/v1/workflows/${workflowId}/schedules/${scheduleId}`, data)
    return res.data
  },

  deleteSchedule: async (workflowId: string, scheduleId: string): Promise<void> => {
    await api.delete(`/api/v1/workflows/${workflowId}/schedules/${scheduleId}`)
  },

  // SSE streaming execution
  runStream: async (
    workflowId: string,
    inputData: Record<string, any>,
    onEvent: (event: SSEEvent) => void,
    onDone: () => void,
    onError: (err: string) => void
  ): Promise<() => void> => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
    const token = useAuthStore.getState().auth.accessToken

    const controller = new AbortController()

    fetch(`${baseUrl}/api/v1/workflows/${workflowId}/executions/stream`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ input_data: inputData }),
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const reader = res.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const parts = buffer.split('\n\n')
          buffer = parts.pop() ?? ''
          for (const part of parts) {
            const line = part.trim()
            if (line.startsWith('data: ')) {
              try {
                const evt = JSON.parse(line.slice(6)) as SSEEvent
                onEvent(evt)
              } catch {
                // ignore malformed chunks
              }
            }
          }
        }
        onDone()
      })
      .catch((err) => {
        if (err.name !== 'AbortError') onError(String(err))
      })

    return () => controller.abort()
  },
}
