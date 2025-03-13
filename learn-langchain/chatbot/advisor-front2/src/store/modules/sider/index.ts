import { defineStore } from 'pinia'
import { getLocalState, SiderState } from './helper'


export const useSiderStore = defineStore('sider-store', {
  state: (): SiderState => getLocalState(),

  getters: {
    getChatSiderSearchQuery(state: SiderState) {
      return state.searchQuery
    }
  },

  actions: {
    setChatSiderSearchQuery(query: string) {
      this.searchQuery = query
    },
  },
})
