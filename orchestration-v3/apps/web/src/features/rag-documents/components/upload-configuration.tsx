import { useMemo } from 'react'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { RagGroup, RagKey } from '@/api/rag-groups'

interface UploadConfigurationProps {
  ragType: 'user_isolated' | 'chatbot_shared' | 'natural_search'
  setRagType: (value: 'user_isolated' | 'chatbot_shared' | 'natural_search') => void
  ragKey: string
  setRagKey: (value: string) => void
  ragGroup: string
  setRagGroup: (value: string) => void
  tags: string
  setTags: (value: string) => void
  groups: RagGroup[]
  keys: RagKey[]
}

export function UploadConfiguration({
  ragType,
  setRagType,
  ragKey,
  setRagKey,
  ragGroup,
  setRagGroup,
  tags,
  setTags,
  groups,
  keys,
}: UploadConfigurationProps) {
  const filteredKeys = useMemo(
    () => (ragGroup ? keys.filter((k) => k.rag_group === ragGroup) : keys),
    [keys, ragGroup]
  )

  const handleGroupChange = (value: string) => {
    setRagGroup(value)
    setRagKey('')
  }

  const handleKeyChange = (value: string) => {
    setRagKey(value)
    const found = keys.find((k) => k.rag_key === value)
    if (found) setRagType(found.rag_type as 'user_isolated' | 'chatbot_shared' | 'natural_search')
  }

  const selectedGroup = groups.find((g) => g.name === ragGroup)

  return (
    <div className='grid gap-4 md:grid-cols-2'>
      {/* Group */}
      <div className='space-y-2'>
        <Label>그룹 *</Label>
        {groups.length > 0 ? (
          <Select value={ragGroup} onValueChange={handleGroupChange}>
            <SelectTrigger>
              <SelectValue placeholder='그룹 선택' />
            </SelectTrigger>
            <SelectContent>
              {groups.map((g) => (
                <SelectItem key={g.id} value={g.name}>
                  <span className='flex items-center gap-2'>
                    <span className='inline-block w-2.5 h-2.5 rounded-full' style={{ backgroundColor: g.color }} />
                    {g.name}
                    <span className='text-muted-foreground text-xs'>({g.key_count}인덱스 · {g.doc_count}문서)</span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <input
            placeholder='그룹 이름 입력'
            value={ragGroup}
            onChange={(e) => setRagGroup(e.target.value)}
            className='flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring'
          />
        )}
        <p className='text-xs text-muted-foreground'>
          {groups.length === 0 ? '그룹 관리 탭에서 그룹을 먼저 생성하세요.' : '인덱스를 묶는 그룹을 선택합니다.'}
        </p>
      </div>

      {/* Collection */}
      <div className='space-y-2'>
        <Label>인덱스 *</Label>
        {filteredKeys.length > 0 ? (
          <Select value={ragKey} onValueChange={handleKeyChange} disabled={!ragGroup}>
            <SelectTrigger>
              <SelectValue placeholder={ragGroup ? 'RAG 키 선택' : '그룹을 먼저 선택하세요'} />
            </SelectTrigger>
            <SelectContent>
              {filteredKeys.map((k) => (
                <SelectItem key={k.id} value={k.rag_key}>
                  <span className='flex items-center gap-2'>
                    <span className='font-mono'>{k.rag_key}</span>
                    <span className='text-muted-foreground text-xs'>({k.doc_count}문서)</span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <input
            placeholder={ragGroup ? '인덱스 ID 입력 (신규 생성)' : '그룹을 먼저 선택하세요'}
            value={ragKey}
            onChange={(e) => setRagKey(e.target.value)}
            disabled={!ragGroup}
            required
            className='flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50'
          />
        )}
        <p className='text-xs text-muted-foreground'>
          {selectedGroup && filteredKeys.length === 0
            ? `"${selectedGroup.name}" 그룹에 인덱스가 없습니다. 인덱스 관리 탭에서 추가하세요.`
            : '기존 인덱스를 선택하면 같은 인덱스에 문서가 추가됩니다.'}
        </p>
      </div>

      {/* Type */}
      <div className='space-y-2 md:col-span-2'>
        <Label>RAG Type</Label>
        <Select value={ragType} onValueChange={(val: never) => setRagType(val)}>
          <SelectTrigger>
            <SelectValue placeholder='타입 선택' />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value='natural_search'>Natural Search (Knowledge Base)</SelectItem>
            <SelectItem value='user_isolated'>User Isolated (Private)</SelectItem>
            <SelectItem value='chatbot_shared'>Chatbot Shared (Global)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Tags */}
      <div className='space-y-2 md:col-span-2'>
        <Label htmlFor='tags'>Tags</Label>
        <input
          id='tags'
          placeholder='쉼표로 구분 (예: manual, v2, 2024)'
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          className='flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring'
        />
      </div>
    </div>
  )
}
