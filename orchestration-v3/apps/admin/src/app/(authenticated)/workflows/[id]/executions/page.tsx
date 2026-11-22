import { WorkflowExecutions } from '@/features/workflows/executions'

interface Props {
  params: Promise<{ id: string }>
}

export default async function ExecutionsPage({ params }: Props) {
  const { id } = await params
  return <WorkflowExecutions workflowId={id} />
}
