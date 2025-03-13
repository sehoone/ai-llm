import { computed } from 'vue'
import { enUS, esAR, koKR } from 'naive-ui'
import { useAppStore } from '@/store'
import { setLocale } from '@/locales'

export function useLanguage() {
  const appStore = useAppStore()

  const language = computed(() => {
    setLocale(appStore.language)
    switch (appStore.language) {
      case 'en-US':
        return enUS
      case 'es-ES':
        return esAR
      case 'ko-KR':
        return koKR
      default:
        return koKR
    }
  })

  return { language }
}
