'use client'

/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type NodeTypes,
  type Node,
  type Edge,
  BackgroundVariant,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { workflowApi, type Workflow, type SSEEvent } from '@/api/workflows'
import { NodePalette } from './components/node-palette'
import { ConfigPanel } from './components/config-panel'
import { ExecutionPanel, type ExecutionLog } from './components/execution-panel'
import { RunDialog } from './components/run-dialog'
import { StartNode } from './components/nodes/start-node'
import { EndNode } from './components/nodes/end-node'
import { LLMNode } from './components/nodes/llm-node'
import { ConditionNode } from './components/nodes/condition-node'
import { RAGNode } from './components/nodes/rag-node'
import { HTTPNode } from './components/nodes/http-node'
import { CodeNode } from './components/nodes/code-node'
import { ToolNode } from './components/nodes/tool-node'
import { LoopNode } from './components/nodes/loop-node'
import { SettingsDrawer } from './components/settings-drawer'
import { Header } from '@/components/layout/header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Save, Play, Globe, ArrowLeft, Loader2, History, Settings } from 'lucide-react'
import { toast } from 'sonner'
import { logger } from '@/lib/logger'

// ── Custom node type map ──────────────────────────────────────────────────────
const NODE_TYPES: NodeTypes = {
  start: StartNode,
  end: EndNode,
  llm: LLMNode,
  condition: ConditionNode,
  rag: RAGNode,
  http: HTTPNode,
  code: CodeNode,
  tool: ToolNode,
  loop: LoopNode,
}

// ── Counter for unique node IDs per session ───────────────────────────────────
let nodeCounter = 1

interface WorkflowEditorProps {
  workflowId?: string  // undefined = new workflow
}

export function WorkflowEditor({ workflowId }: WorkflowEditorProps) {
  const router = useRouter()
  const reactFlowWrapper = useRef<HTMLDivElement>(null)

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  // Editor state
  const [workflowName, setWorkflowName] = useState('새 워크플로우')
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isPublishing, setIsPublishing] = useState(false)

  const [settingsOpen, setSettingsOpen] = useState(false)

  // Execution state
  const [runDialogOpen, setRunDialogOpen] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [executionLogs, setExecutionLogs] = useState<ExecutionLog[]>([])
  const [finalOutput, setFinalOutput] = useState<Record<string, any> | null>(null)
  const [executionError, setExecutionError] = useState<string | null>(null)
  const stopStreamRef = useRef<(() => void) | null>(null)

  // ── Load existing workflow ──────────────────────────────────────────────────
  useEffect(() => {
    if (!workflowId) return
    workflowApi.get(workflowId).then((wf) => {
      setWorkflow(wf)
      setWorkflowName(wf.name)
      const { nodes: defNodes = [], edges: defEdges = [] } = wf.definition
      setNodes(defNodes as Node[])
      setEdges(defEdges as Edge[])
    }).catch((err) => {
      logger.error('Failed to load workflow', err)
      toast.error('워크플로우를 불러오지 못했습니다')
    })
  }, [workflowId, setNodes, setEdges])

  // ── Selected node ───────────────────────────────────────────────────────────
  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id)
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  // ── Edge connect ────────────────────────────────────────────────────────────
  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: false }, eds)),
    [setEdges]
  )

  // ── Drop from palette ───────────────────────────────────────────────────────
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const type = e.dataTransfer.getData('application/workflow-node-type')
      if (!type || !reactFlowWrapper.current) return

      const rect = reactFlowWrapper.current.getBoundingClientRect()
      const position = {
        x: e.clientX - rect.left - 100,
        y: e.clientY - rect.top - 40,
      }

      const id = `${type}-${nodeCounter++}`
      const newNode: Node = {
        id,
        type,
        position,
        data: getDefaultData(type),
      }
      setNodes((nds) => [...nds, newNode])
      setSelectedNodeId(id)
    },
    [setNodes]
  )

  // ── Update node data (from ConfigPanel) ─────────────────────────────────────
  const updateNodeData = useCallback(
    (nodeId: string, data: Record<string, any>) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === nodeId ? { ...n, data } : n))
      )
    },
    [setNodes]
  )

  // ── Apply execution status overlays ─────────────────────────────────────────
  const applyNodeStatus = useCallback(
    (nodeId: string, status: string) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, __status: status } } : n))
      )
    },
    [setNodes]
  )

  const clearNodeStatuses = useCallback(() => {
    setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, __status: undefined } })))
  }, [setNodes])

  // ── Save ────────────────────────────────────────────────────────────────────
  const handleSave = async () => {
    setIsSaving(true)
    try {
      const definition = { nodes, edges } as any
      if (workflow) {
        const updated = await workflowApi.update(workflow.id, { name: workflowName, definition })
        setWorkflow(updated)
        toast.success('저장됨')
      } else {
        const created = await workflowApi.create({ name: workflowName, definition })
        setWorkflow(created)
        toast.success('워크플로우 생성됨')
        router.replace(`/workflows/${created.id}/edit`)
      }
    } catch (err) {
      logger.error('Save failed', err)
      toast.error('저장에 실패했습니다')
    } finally {
      setIsSaving(false)
    }
  }

  // ── Publish toggle ──────────────────────────────────────────────────────────
  const handlePublish = async () => {
    if (!workflow) { toast.error('먼저 저장하세요'); return }
    setIsPublishing(true)
    try {
      const updated = await workflowApi.togglePublish(workflow.id)
      setWorkflow(updated)
      toast.success(updated.is_published ? '발행됨' : '발행 해제됨')
    } catch (err) {
      logger.error('Publish failed', err)
      toast.error('발행 실패')
    } finally {
      setIsPublishing(false)
    }
  }

  // ── Run ─────────────────────────────────────────────────────────────────────
  const handleRunClick = () => {
    if (!workflow) { toast.error('먼저 저장하세요'); return }
    setRunDialogOpen(true)
  }

  const handleRun = async (inputData: Record<string, any>) => {
    if (!workflow) return
    setRunDialogOpen(false)
    setIsRunning(true)
    setExecutionLogs([])
    setFinalOutput(null)
    setExecutionError(null)
    clearNodeStatuses()

    const stop = await workflowApi.runStream(
      workflow.id,
      inputData,
      (event: SSEEvent) => {
        setExecutionLogs((prev) => [
          ...prev,
          { id: `${Date.now()}-${Math.random()}`, event, timestamp: new Date() },
        ])
        // Update node status overlays
        if (event.type === 'node_start') applyNodeStatus(event.node_id, 'running')
        if (event.type === 'node_complete') applyNodeStatus(event.node_id, 'completed')
        if (event.type === 'node_failed') applyNodeStatus(event.node_id, 'failed')
        if (event.type === 'node_skipped') applyNodeStatus(event.node_id, 'skipped')
        if (event.type === 'execution_complete') setFinalOutput(event.output_data)
        if (event.type === 'execution_failed') setExecutionError(event.error)
      },
      () => setIsRunning(false),
      (err) => {
        setExecutionError(err)
        setIsRunning(false)
        toast.error('실행 실패: ' + err)
      }
    )
    stopStreamRef.current = stop
  }

  // Cleanup on unmount
  useEffect(() => () => { stopStreamRef.current?.() }, [])

  // ── Start node variables (for RunDialog) ────────────────────────────────────
  const startNode = nodes.find((n) => n.type === 'start')
  const startVariables: any[] = (startNode?.data as any)?.variables ?? []

  return (
    <div className='flex flex-col h-screen'>
      {/* ── Toolbar ── */}
      <Header>
        <Button variant='ghost' size='sm' onClick={() => router.push('/workflows')}>
          <ArrowLeft className='h-4 w-4 mr-1' />
          워크플로우
        </Button>
        <div className='mx-3 h-5 w-px bg-border' />
        <Input
          value={workflowName}
          onChange={(e) => setWorkflowName(e.target.value)}
          className='h-8 w-56 text-sm font-medium border-0 shadow-none focus-visible:ring-0 px-1'
          placeholder='워크플로우 이름'
        />
        {workflow?.is_published && (
          <Badge variant='secondary' className='text-xs ml-2'>Published</Badge>
        )}
        <div className='ml-auto flex items-center gap-2'>
          {workflow && (
            <Button
              size='sm'
              variant='ghost'
              onClick={() => router.push(`/workflows/${workflow.id}/executions`)}
            >
              <History className='h-3.5 w-3.5 mr-1' />
              실행 기록
            </Button>
          )}
          {workflow && (
            <Button
              size='sm'
              variant='ghost'
              onClick={() => setSettingsOpen((o) => !o)}
            >
              <Settings className='h-3.5 w-3.5 mr-1' />
              설정
            </Button>
          )}
          <Button
            size='sm'
            variant='outline'
            onClick={handlePublish}
            disabled={isPublishing || !workflow}
          >
            {isPublishing ? <Loader2 className='h-3.5 w-3.5 animate-spin mr-1' /> : <Globe className='h-3.5 w-3.5 mr-1' />}
            {workflow?.is_published ? '발행 해제' : '발행'}
          </Button>
          <Button size='sm' variant='outline' onClick={handleSave} disabled={isSaving}>
            {isSaving ? <Loader2 className='h-3.5 w-3.5 animate-spin mr-1' /> : <Save className='h-3.5 w-3.5 mr-1' />}
            저장
          </Button>
          <Button size='sm' onClick={handleRunClick} disabled={isRunning}>
            {isRunning
              ? <Loader2 className='h-3.5 w-3.5 animate-spin mr-1' />
              : <Play className='h-3.5 w-3.5 mr-1' />}
            실행
          </Button>
        </div>
      </Header>

      {/* ── Main area ── */}
      <div className='flex flex-1 overflow-hidden'>
        {/* Left: Node Palette */}
        <NodePalette className='w-52 shrink-0' />

        {/* Center: Canvas */}
        <div ref={reactFlowWrapper} className='flex-1 flex flex-col overflow-hidden' style={{ colorScheme: 'light' }}>
          <div className='flex-1' onDragOver={onDragOver} onDrop={onDrop}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={NODE_TYPES}
              fitView
              className='bg-muted/20'
              deleteKeyCode={['Backspace', 'Delete']}
            >
              <Background variant={BackgroundVariant.Dots} gap={16} size={1} className='opacity-40' />
              <Controls className='rounded-lg border shadow-sm' />
              <MiniMap
                className='rounded-lg border shadow-sm'
                nodeColor={(n) => nodeColor(n.type ?? '')}
              />
            </ReactFlow>
          </div>

          {/* Bottom: Execution Panel */}
          <ExecutionPanel
            logs={executionLogs}
            isRunning={isRunning}
            finalOutput={finalOutput}
            error={executionError}
          />
        </div>

        {/* Right: Config Panel */}
        {selectedNode && (
          <ConfigPanel
            node={selectedNode as any}
            onUpdate={updateNodeData}
            onClose={() => setSelectedNodeId(null)}
            className='w-72 shrink-0'
          />
        )}
      </div>

      {/* Run Dialog */}
      <RunDialog
        open={runDialogOpen}
        variables={startVariables}
        onRun={handleRun}
        onClose={() => setRunDialogOpen(false)}
      />

      {/* Settings Drawer */}
      <SettingsDrawer
        open={settingsOpen}
        workflow={workflow}
        onClose={() => setSettingsOpen(false)}
        onWebhookChange={(token) => setWorkflow((wf) => wf ? { ...wf, webhook_token: token } : wf)}
        className='w-96'
      />
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getDefaultData(type: string): Record<string, any> {
  switch (type) {
    case 'start': return { variables: [] }
    case 'end': return { outputs: [] }
    case 'llm': return { model: 'gpt-4o-mini', system_prompt: '', prompt: '' }
    case 'condition': return { left: '', operator: 'not_empty', right: '' }
    case 'rag': return { rag_key: '', rag_type: 'chatbot_shared', query: '', limit: 5 }
    case 'http': return { url: '', method: 'GET', headers: {}, body: '', timeout: 30 }
    case 'code': return { code: '# result = {}\nresult = {}' }
    case 'tool': return { tool: 'web_search', query: '' }
    case 'loop': return { items: '', item_var: 'item', processor: 'passthrough' }
    default: return {}
  }
}

function nodeColor(type: string): string {
  switch (type) {
    case 'start': return '#22c55e'
    case 'end': return '#f97316'
    case 'llm': return '#a855f7'
    case 'condition': return '#f59e0b'
    case 'rag': return '#06b6d4'
    case 'http': return '#3b82f6'
    case 'code': return '#64748b'
    case 'tool': return '#f43f5e'
    case 'loop': return '#7c3aed'
    default: return '#94a3b8'
  }
}
