'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { UploadForm } from './components/upload-form'
import { UploadInstructions } from './components/upload-instructions'

export default function RagUpload() {
  return (
    <div className='flex flex-col gap-4 p-4 md:p-8'>
      <div className='flex items-center justify-between space-y-2'>
        <h2 className='text-3xl font-bold tracking-tight'>
          RAG Document Upload
        </h2>
      </div>

      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3'>
        <Card className='md:col-span-2'>
          <CardHeader>
            <CardTitle>Upload Document</CardTitle>
          </CardHeader>
          <CardContent>
            <UploadForm />
          </CardContent>
        </Card>

        <div className='space-y-4'>
          <UploadInstructions />
        </div>
      </div>
    </div>
  )
}

