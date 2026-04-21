import { useEffect } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { type z } from 'zod'
import { type LLMResource, llmResourceSchema } from '../data/schema'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface LLMResourceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  resource?: LLMResource
  onSubmit: (data: LLMResource) => Promise<void>
}

const DEFAULT_VALUES = {
  name: '',
  resource_type: 'chat' as const,
  model_name: '',
  provider: 'openai',
  api_base: '',
  api_key: '',
  deployment_name: '',
  api_version: '',
  region: '',
  priority: 0,
  weight: 1,
  is_active: true,
}

export function LLMResourceDialog({
  open,
  onOpenChange,
  resource,
  onSubmit,
}: LLMResourceDialogProps) {
  const form = useForm<z.input<typeof llmResourceSchema>, unknown, LLMResource>({
    resolver: zodResolver(llmResourceSchema),
    defaultValues: DEFAULT_VALUES,
  })

  const provider = useWatch({ control: form.control, name: 'provider' })
  const isAzure = provider === 'azure'

  useEffect(() => {
    form.reset(resource ?? DEFAULT_VALUES)
  }, [resource, form, open])

  const handleSubmit = async (data: LLMResource) => {
    await onSubmit(data)
    form.reset()
    onOpenChange(false)
  }

  const getApiBasePlaceholder = (p: string) => {
    switch (p) {
      case 'azure':
        return 'https://{resource-name}.openai.azure.com/'
      case 'anthropic':
        return 'https://api.anthropic.com'
      case 'google':
        return 'https://generativelanguage.googleapis.com'
      case 'ollama':
        return 'http://localhost:11434'
      case 'openai':
      default:
        return 'https://api.openai.com/v1'
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className='sm:max-w-[480px] overflow-y-auto max-h-[85vh]'>
        <DialogHeader>
          <DialogTitle>
            {resource ? 'Edit Resource' : 'Add Resource'}
          </DialogTitle>
          <DialogDescription>
            {resource
              ? 'Make changes to your LLM resource here.'
              : 'Add a new LLM resource to your system.'}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className='space-y-4'>

            {/* Resource Type */}
            <FormField
              control={form.control}
              name='resource_type'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Resource Type</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder='Select type' />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value='chat'>Chat (LLM)</SelectItem>
                      <SelectItem value='embedding'>Embedding</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Provider */}
            <FormField
              control={form.control}
              name='provider'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Provider</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder='Select a provider' />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value='openai'>OpenAI</SelectItem>
                      <SelectItem value='azure'>Azure OpenAI (AI Foundry)</SelectItem>
                      <SelectItem value='anthropic'>Anthropic (Claude)</SelectItem>
                      <SelectItem value='google'>Google (Gemini)</SelectItem>
                      <SelectItem value='ollama'>Ollama (Local)</SelectItem>
                      <SelectItem value='other'>Other</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Name */}
            <FormField
              control={form.control}
              name='name'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Resource Name</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder={isAzure ? 'e.g. azure-gpt4o-eastus' : 'e.g. my-openai'} />
                  </FormControl>
                  <FormDescription>관리용 식별자 (중복 허용)</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Model Name */}
            <FormField
              control={form.control}
              name='model_name'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Model Name <span className='text-muted-foreground font-normal'>(호출 선택 키)</span></FormLabel>
                  <FormControl>
                    <Input {...field} value={field.value || ''} placeholder='e.g. gpt-4o' />
                  </FormControl>
                  <FormDescription>
                    {isAzure
                      ? 'LLM 호출 시 사용할 논리명. 동일 모델의 멀티 리전 배포를 하나의 키로 묶습니다.'
                      : 'LLM 호출 시 사용할 논리적 모델명'}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* API Base */}
            <FormField
              control={form.control}
              name='api_base'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>API Base URL {isAzure && <span className='text-muted-foreground font-normal'>(Target URL)</span>}</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder={getApiBasePlaceholder(provider)} autoComplete='off' />
                  </FormControl>
                  {isAzure && (
                    <FormDescription>Azure AI Foundry의 리전별 엔드포인트 URL</FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* API Key */}
            <FormField
              control={form.control}
              name='api_key'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>API Key</FormLabel>
                  <FormControl>
                    <Input {...field} type='password' autoComplete='off' />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Azure-specific section */}
            {isAzure && (
              <div className='rounded-md border p-4 space-y-4 bg-muted/30'>
                <p className='text-sm font-medium text-muted-foreground'>Azure AI Foundry 설정</p>

                <FormField
                  control={form.control}
                  name='deployment_name'
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Deployment Name</FormLabel>
                      <FormControl>
                        <Input {...field} value={field.value || ''} placeholder='e.g. gpt4o-deployment' />
                      </FormControl>
                      <FormDescription>Azure 포털에서 설정한 배포명</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className='grid grid-cols-2 gap-4'>
                  <FormField
                    control={form.control}
                    name='api_version'
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>API Version</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value || ''} placeholder='e.g. 2024-08-01-preview' />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name='region'
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Region</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value || ''} placeholder='e.g. eastus' />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            )}

            {/* Non-Azure: deployment_name + region */}
            {!isAzure && (
              <div className='grid grid-cols-2 gap-4'>
                <FormField
                  control={form.control}
                  name='deployment_name'
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Deployment Name</FormLabel>
                      <FormControl>
                        <Input {...field} value={field.value || ''} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name='region'
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Region</FormLabel>
                      <FormControl>
                        <Input {...field} value={field.value || ''} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            )}

            {/* Priority + Weight */}
            <div className='grid grid-cols-2 gap-4'>
              <FormField
                control={form.control}
                name='priority'
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Priority</FormLabel>
                    <FormControl>
                      <Input type='number' {...field} value={field.value as number} />
                    </FormControl>
                    <FormDescription>높을수록 먼저 시도</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name='weight'
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Weight</FormLabel>
                    <FormControl>
                      <Input type='number' min={1} {...field} value={field.value as number} />
                    </FormControl>
                    <FormDescription>동일 priority 내 분산 비율</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Is Active */}
            <FormField
              control={form.control}
              name='is_active'
              render={({ field }) => (
                <FormItem className='flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4'>
                  <FormControl>
                    <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                  <div className='space-y-1 leading-none'>
                    <FormLabel>Active</FormLabel>
                  </div>
                </FormItem>
              )}
            />

            <Button type='submit' className='w-full'>Save</Button>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
