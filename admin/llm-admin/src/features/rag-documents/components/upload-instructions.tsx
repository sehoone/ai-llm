import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function UploadInstructions() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className='text-sm font-medium'>Instructions</CardTitle>
      </CardHeader>
      <CardContent className='text-sm space-y-2 text-muted-foreground'>
        <p>
          RAG 지식 베이스에 포함할 문서를 여기에 업로드하세요. 지원되는 형식은{' '}
          <strong>PDF</strong>, <strong>Microsoft Word (DOCX)</strong>, 및 일반
          텍스트 파일입니다.
        </p>
        <p>
          <strong>RAG Key:</strong> 문서 컬렉션의 주요 식별자입니다. "자연어
          검색" 페이지에서 이 키를 사용하여 문서 내를 검색할 수 있습니다.
        </p>
        <p>
          <strong>RAG Type:</strong> User Isolated는 사용자 본인만 문서를 볼 수
          있음을 의미합니다. Chatbot Shared는 전역적으로 사용 가능함을 의미합니다(예:
          특정 챗봇의 모든 사용자).
        </p>
      </CardContent>
    </Card>
  )
}
