'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import * as api from '@/api/sample'
import { Section, JsonResult } from '../section'

type UserSummary = { id: number; username: string; email: string; role: string; status: string }

export function TabDatabase() {
  const [health, setHealth] = useState<unknown>(null)
  const [users, setUsers] = useState<UserSummary[] | null>(null)
  const [userCount, setUserCount] = useState<unknown>(null)
  const [poolStats, setPoolStats] = useState<unknown>(null)
  const [usersLoading, setUsersLoading] = useState(false)

  const handleLoadUsers = async () => {
    setUsersLoading(true)
    try { setUsers(await api.getDbUsers()) }
    finally { setUsersLoading(false) }
  }

  return (
    <div className='space-y-4'>
      <Section title='DB 연결 상태' endpoint='/api/v1/sample/db/health'>
        <p className='mb-2 text-xs text-muted-foreground'>
          DatabaseService 믹스인 패턴: UserRepository + SessionRepository + ... 합성
        </p>
        <Button size='sm' onClick={async () => setHealth(await api.getDbHealth())}>조회</Button>
        <JsonResult data={health} />
      </Section>

      <Section title='사용자 목록 (Depends 패턴)' endpoint='/api/v1/sample/db/users'>
        <p className='mb-2 text-xs text-muted-foreground'>
          FastAPI Depends(get_session) 주입 패턴 — 라우트 계층의 표준 세션 관리
        </p>
        <Button size='sm' onClick={handleLoadUsers} disabled={usersLoading}>
          {usersLoading ? '조회 중…' : '조회'}
        </Button>
        {users && users.length > 0 && (
          <div className='mt-2 overflow-auto rounded-md border'>
            <table className='w-full text-xs'>
              <thead className='bg-muted'>
                <tr>
                  {['ID', 'Username', 'Email', 'Role', 'Status'].map((h) => (
                    <th key={h} className='px-3 py-2 text-left font-medium'>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className='border-t'>
                    <td className='px-3 py-1.5'>{u.id}</td>
                    <td className='px-3 py-1.5'>{u.username}</td>
                    <td className='px-3 py-1.5'>{u.email}</td>
                    <td className='px-3 py-1.5'>{u.role}</td>
                    <td className='px-3 py-1.5'>{u.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {users && users.length === 0 && (
          <p className='mt-2 text-xs text-muted-foreground'>사용자가 없습니다.</p>
        )}
      </Section>

      <Section title='사용자 수 (managed_session 패턴)' endpoint='/api/v1/sample/db/users/count'>
        <p className='mb-2 text-xs text-muted-foreground'>
          서비스 레이어에서 managed_session 직접 사용 — 자동 rollback + 에러 로깅
        </p>
        <Button size='sm' onClick={async () => setUserCount(await api.getDbUserCount())}>조회</Button>
        <JsonResult data={userCount} />
      </Section>

      <Section title='커넥션 풀 상태' endpoint='/api/v1/sample/db/pool-stats'>
        <p className='mb-2 text-xs text-muted-foreground'>
          QueuePool: size=20, max_overflow=10, pool_pre_ping=True
        </p>
        <Button size='sm' onClick={async () => setPoolStats(await api.getDbPoolStats())}>조회</Button>
        <JsonResult data={poolStats} />
      </Section>
    </div>
  )
}
