/* eslint-disable @typescript-eslint/no-explicit-any */
import api from './axios'

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

export interface WorkflowEndpoint {
  id: string
  workflow_id: string
  user_id: number
  path: string
  method: string
  is_active: boolean
  description: string
  created_at: string
  updated_at: string
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
    const res = await api.get('v1/workflows', { params: { limit, offset } })
    return res.data
  },

  get: async (id: string): Promise<Workflow> => {
    const res = await api.get(`v1/workflows/${id}`)
    return res.data
  },

  create: async (data: { name: string; description?: string; definition?: WorkflowDefinition }): Promise<Workflow> => {
    const res = await api.post('v1/workflows', data)
    return res.data
  },

  update: async (
    id: string,
    data: { name?: string; description?: string; definition?: WorkflowDefinition; is_published?: boolean }
  ): Promise<Workflow> => {
    const res = await api.put(`v1/workflows/${id}`, data)
    return res.data
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`v1/workflows/${id}`)
  },

  togglePublish: async (id: string): Promise<Workflow> => {
    const res = await api.patch(`v1/workflows/${id}/publish`)
    return res.data
  },

  // Node types palette
  getNodeTypes: async (): Promise<NodeType[]> => {
    const res = await api.get('v1/workflows/node-types')
    return res.data
  },

  // Executions
  run: async (workflowId: string, inputData: Record<string, any>): Promise<WorkflowExecution> => {
    const res = await api.post(`v1/workflows/${workflowId}/executions`, { input_data: inputData })
    return res.data
  },

  listExecutions: async (workflowId: string): Promise<ExecutionListItem[]> => {
    const res = await api.get(`v1/workflows/${workflowId}/executions`)
    return res.data
  },

  getExecution: async (executionId: string): Promise<WorkflowExecution> => {
    const res = await api.get(`v1/workflows/executions/${executionId}`)
    return res.data
  },

  // Webhook management
  manageWebhook: async (workflowId: string, action: 'generate' | 'revoke'): Promise<{ webhook_token: string | null }> => {
    const res = await api.patch(`v1/workflows/${workflowId}/webhook`, null, { params: { action } })
    return res.data
  },

  // Schedule CRUD
  listSchedules: async (workflowId: string): Promise<WorkflowSchedule[]> => {
    const res = await api.get(`v1/workflows/${workflowId}/schedules`)
    return res.data
  },

  createSchedule: async (
    workflowId: string,
    data: { label?: string; cron_expr: string; input_data?: Record<string, any> }
  ): Promise<WorkflowSchedule> => {
    const res = await api.post(`v1/workflows/${workflowId}/schedules`, data)
    return res.data
  },

  updateSchedule: async (
    workflowId: string,
    scheduleId: string,
    data: Partial<{ label: string; cron_expr: string; input_data: Record<string, any>; is_active: boolean }>
  ): Promise<WorkflowSchedule> => {
    const res = await api.patch(`v1/workflows/${workflowId}/schedules/${scheduleId}`, data)
    return res.data
  },

  deleteSchedule: async (workflowId: string, scheduleId: string): Promise<void> => {
    await api.delete(`v1/workflows/${workflowId}/schedules/${scheduleId}`)
  },

  // Dynamic API endpoint CRUD
  listEndpoints: async (workflowId: string): Promise<WorkflowEndpoint[]> => {
    const res = await api.get(`v1/workflows/${workflowId}/endpoints`)
    return res.data
  },

  createEndpoint: async (
    workflowId: string,
    data: { path: string; method: string; description?: string; is_active?: boolean }
  ): Promise<WorkflowEndpoint> => {
    const res = await api.post(`v1/workflows/${workflowId}/endpoints`, data)
    return res.data
  },

  updateEndpoint: async (
    workflowId: string,
    endpointId: string,
    data: Partial<{ path: string; method: string; description: string; is_active: boolean }>
  ): Promise<WorkflowEndpoint> => {
    const res = await api.put(`v1/workflows/${workflowId}/endpoints/${endpointId}`, data)
    return res.data
  },

  deleteEndpoint: async (workflowId: string, endpointId: string): Promise<void> => {
    await api.delete(`v1/workflows/${workflowId}/endpoints/${endpointId}`)
  },

  // SSE streaming execution
  runStream: async (
    workflowId: string,
    inputData: Record<string, any>,
    onEvent: (event: SSEEvent) => void,
    onDone: () => void,
    onError: (err: string) => void
  ): Promise<() => void> => {
    const controller = new AbortController()

    let buffer = ''
    let processedIndex = 0

    api
      .post(
        `v1/workflows/${workflowId}/executions/stream`,
        { input_data: inputData },
        {
          signal: controller.signal,
          onDownloadProgress: (progressEvent) => {
            const xhr = progressEvent.event?.target as any
            if (!xhr) return

            const responseText: string = xhr.responseText || ''
            const newContent = responseText.substring(processedIndex)
            processedIndex = responseText.length

            buffer += newContent
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
          },
        }
      )
      .then(() => onDone())
      .catch((err) => {
        if (err.code !== 'ERR_CANCELED') onError(String(err))
      })

    return () => controller.abort()
  },
}
