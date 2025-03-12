import type { GlobalThemeOverrides } from 'naive-ui'
import { computed, watch } from 'vue'
import { darkTheme, useOsTheme } from 'naive-ui'
import { useAppStore } from '@/store'

export function useTheme() {
  const appStore = useAppStore()

  const OsTheme = useOsTheme()

  const isDark = computed(() => {
    if (appStore.theme === 'auto')
      return OsTheme.value === 'dark'
    else
      return appStore.theme === 'dark'
  })

  const theme = computed(() => {
    return isDark.value ? darkTheme : undefined
  })

  const themeOverrides = computed<GlobalThemeOverrides>(() => {
    if (isDark.value) {
      return {
        common: {
          // primaryColor: '#2080f0',
          // primaryColorHover: '#2080f0',
          // primaryColorPressed: '#2080f0',
          // infoColor: '#2080f0',
        },
      }
    }
    return {
      common: {
        // baseColor: '#2080f0',
        primaryColor: '#2080f0',
        primaryColorHover: '#2080f0',
        primaryColorPressed: '#2080f0',
        infoColor: '#2080f0',
        // actionColor: '#2080f0',
        pressedColor: '#2080f0',
      },
    }
  })

  watch(
    () => isDark.value,
    (dark) => {
      if (dark)
        document.documentElement.classList.add('dark')
      else
        document.documentElement.classList.remove('dark')
    },
    { immediate: true },
  )

  return { theme, themeOverrides }
}
