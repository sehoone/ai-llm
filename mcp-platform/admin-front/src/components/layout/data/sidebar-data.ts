import {
  Command,
  Key,
  LayoutDashboard,
  Users,
} from 'lucide-react'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: 'sehoon',
    email: 'sehoone@github.com',
    avatar: '',
  },
  teams: [
    {
      name: 'MCP Admin',
      logo: Command,
      plan: 'API Key Management',
    },
  ],
  navGroups: [
    {
      title: 'General',
      items: [
        {
          title: 'Dashboard',
          url: '/',
          icon: LayoutDashboard,
        },
        {
          title: 'User Management',
          url: '/users',
          icon: Users,
        },
      ],
    },
    {
      title: 'Configuration',
      items: [
        {
          title: 'API Keys',
          url: '/api-keys',
          icon: Key,
        },
      ],
    },
  ],
}
