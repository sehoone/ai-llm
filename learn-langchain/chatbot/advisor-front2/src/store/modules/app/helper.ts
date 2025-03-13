import { ss } from '@/utils/storage'

const LOCAL_NAME = 'appSetting'

export type Theme = 'light' | 'dark' | 'auto'

export type Language = 'en-US' | 'es-ES' | 'ko-KR'

const languageMap: { [key: string]: Language } = {
  'en': 'en-US',
  'en-US': 'en-US',
  'es': 'es-ES',
  'es-ES': 'es-ES',
  'ko': 'ko-KR',
  'ko-KR': 'ko-KR',
}

export interface AppState {
  siderCollapsed: boolean
  theme: Theme
  language: Language
}

export function defaultSetting(): AppState {
  const language = languageMap[navigator.language]
  return { siderCollapsed: false, theme: 'light', language }
}

export function getLocalSetting(): AppState {
  const localSetting: AppState | undefined = ss.get(LOCAL_NAME)
  return { ...defaultSetting(), ...localSetting }
}

export function setLocalSetting(setting: AppState): void {
  ss.set(LOCAL_NAME, setting)
}
