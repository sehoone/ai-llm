import { Command, Database, Search } from 'lucide-react'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: 'admin',
    email: 'admin@poc.com',
    avatar: '',
  },
  teams: [
    {
      name: 'Vector Search POC',
      logo: Command,
      plan: 'pgvector Demo',
    },
  ],
  navGroups: [
    {
      title: 'Main',
      items: [
        {
          title: '임베딩 관리',
          url: '/embeddings',
          icon: Database,
        },
        {
          title: '벡터 검색',
          url: '/search',
          icon: Search,
        },
      ],
    },
  ],
}
