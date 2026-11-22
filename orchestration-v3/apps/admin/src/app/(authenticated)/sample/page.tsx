import { Suspense } from 'react'
import { Products } from '@/features/sample'

export default function SamplePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Products />
    </Suspense>
  )
}
