import { ss } from '@/utils/storage'

const LOCAL_NAME = 'siderStorage'

export interface SiderState {
  searchQuery: string
}

export function defaultState(): SiderState {
  return {
    searchQuery: ''
  }
}

export function getLocalState(): SiderState {
  const localState = ss.get(LOCAL_NAME)
  return { ...defaultState(), ...localState }
}

export function setLocalState(state: SiderState) {
  ss.set(LOCAL_NAME, state)
}

// export function setSearchQuery(query: string) {
//   this.searchQuery = query
// }