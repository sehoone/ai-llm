'use client'

/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Play } from 'lucide-react'

interface Variable {
  name: string
  type: string
  required?: boolean
  description?: string
}

interface RunDialogProps {
  open: boolean
  variables: Variable[]
  onRun: (inputData: Record<string, any>) => void
  onClose: () => void
}

export function RunDialog({ open, variables, onRun, onClose }: RunDialogProps) {
  const [values, setValues] = useState<Record<string, string>>({})

  const setValue = (name: string, val: string) =>
    setValues((prev) => ({ ...prev, [name]: val }))

  const handleRun = () => {
    const inputData: Record<string, any> = {}
    for (const v of variables) {
      const raw = values[v.name] ?? ''
      if (v.type === 'number') {
        inputData[v.name] = raw === '' ? undefined : Number(raw)
      } else if (v.type === 'boolean') {
        inputData[v.name] = raw === 'true' || raw === '1'
      } else if (v.type === 'object') {
        try { inputData[v.name] = JSON.parse(raw) } catch { inputData[v.name] = raw }
      } else {
        inputData[v.name] = raw
      }
    }
    onRun(inputData)
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className='max-w-md'>
        <DialogHeader>
          <DialogTitle>워크플로우 실행</DialogTitle>
          <DialogDescription>
            {variables.length > 0
              ? '입력 변수를 채운 후 실행하세요.'
              : '입력 변수가 없습니다. 바로 실행합니다.'}
          </DialogDescription>
        </DialogHeader>

        {variables.length > 0 && (
          <div className='space-y-4 py-2'>
            {variables.map((v) => (
              <div key={v.name} className='space-y-1.5'>
                <Label className='text-sm flex items-center gap-1'>
                  <span className='font-mono'>{v.name}</span>
                  <span className='text-muted-foreground text-xs'>:{v.type}</span>
                  {v.required && <span className='text-red-500'>*</span>}
                </Label>
                {v.description && (
                  <p className='text-[11px] text-muted-foreground'>{v.description}</p>
                )}
                {v.type === 'object' ? (
                  <Textarea
                    value={values[v.name] ?? ''}
                    onChange={(e) => setValue(v.name, e.target.value)}
                    placeholder='{"key": "value"}'
                    className='text-xs font-mono resize-none h-16'
                  />
                ) : (
                  <Input
                    value={values[v.name] ?? ''}
                    onChange={(e) => setValue(v.name, e.target.value)}
                    placeholder={v.type === 'boolean' ? 'true / false' : v.type === 'number' ? '0' : '...'}
                    className='text-sm'
                  />
                )}
              </div>
            ))}
          </div>
        )}

        <DialogFooter>
          <Button variant='outline' onClick={onClose}>취소</Button>
          <Button onClick={handleRun}>
            <Play className='h-4 w-4 mr-2' />
            실행
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
