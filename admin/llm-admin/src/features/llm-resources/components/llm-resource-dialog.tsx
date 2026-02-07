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

export function LLMResourceDialog({
  open,
  onOpenChange,
  resource,
  onSubmit,
}: LLMResourceDialogProps) {
  const form = useForm<z.input<typeof llmResourceSchema>, unknown, LLMResource>({
    resolver: zodResolver(llmResourceSchema),
    defaultValues: {
      name: '',
      provider: 'openai',
      api_base: '',
      api_key: '',
      deployment_name: '',
      api_version: '',
      region: '',
      priority: 0,
      is_active: true,
    },
  })

  // Watch the provider field to update the placeholder
  const provider = useWatch({
    control: form.control,
    name: 'provider',
  })

  useEffect(() => {
    if (resource) {
      form.reset(resource)
    } else {
      form.reset({
        name: '',
        provider: 'openai',
        api_base: '',
        api_key: '',
        deployment_name: '',
        api_version: '',
        region: '',
        priority: 0,
        is_active: true,
      })
    }
  }, [resource, form, open])

  const handleSubmit = async (data: LLMResource) => {
    await onSubmit(data)
    form.reset()
    onOpenChange(false)
  }

  const getPlaceholder = (provider: string) => {
    switch (provider) {
      case 'azure':
        return 'https://{resource}.openai.azure.com/'
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
      <DialogContent className='sm:max-w-[425px] overflow-y-auto max-h-[80vh]'>
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
          <form
            onSubmit={form.handleSubmit(handleSubmit)}
            className='space-y-4'
          >
            <FormField
              control={form.control}
              name='name'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name='provider'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Provider</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a provider" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="azure">Azure OpenAI (AI Foundry)</SelectItem>
                      <SelectItem value="anthropic">Anthropic (Claude)</SelectItem>
                      <SelectItem value="google">Google (Gemini)</SelectItem>
                      <SelectItem value="ollama">Ollama (Local)</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name='api_base'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>API Base URL</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder={getPlaceholder(provider)} autoComplete="off" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
             <FormField
              control={form.control}
              name='api_key'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>API Key</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
             <FormField
              control={form.control}
              name='deployment_name'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Deployment Name (Optional)</FormLabel>
                  <FormControl>
                    <Input {...field} value={field.value || ''} />
                  </FormControl>
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
             <FormField
              control={form.control}
              name='priority'
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Priority</FormLabel>
                  <FormControl>
                    <Input type='number' {...field} value={field.value as number} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name='is_active'
              render={({ field }) => (
                <FormItem className='flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4'>
                  <FormControl>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
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
