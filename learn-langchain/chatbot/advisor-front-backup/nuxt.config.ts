// https://nuxt.com/docs/api/configuration/nuxt-config
import { defineNuxtConfig } from 'nuxt/config'
const appName = process.env.NUXT_PUBLIC_APP_NAME ?? 'ChatGPT UI'
// import Inspector from 'vite-plugin-vue-inspector'
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  ssr: false,
  debug: process.env.NODE_ENV !== 'production',
  app: {
      head: {
          title: appName,
      },
  },
  runtimeConfig: {
      public: {
          appName: appName,
          typewriter: false,
          typewriterDelay: 50,
          customApiKey: false
      }
  },
//   build: {
//       transpile: ['vuetify']
//   },
//   css: [
//       'vuetify/styles',
//       'material-design-icons-iconfont/dist/material-design-icons.css',
//       'highlight.js/styles/panda-syntax-dark.css',
//   ],
//   modules: [
//       '@nuxtjs/color-mode',
//       '@nuxtjs/i18n'
//   ]
})
