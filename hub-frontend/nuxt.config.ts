export default defineNuxtConfig({
  ssr: false,
  devtools: { enabled: true },
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt', '@vueuse/nuxt', '@sentry/nuxt/module'],
  css: ['~/assets/css/main.css'],

  app: {
    head: {
      titleTemplate: '%s · ChatlyAi',
      title: 'ChatlyAi',
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
      ],
    },
  },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
    },
  },

  compatibilityDate: '2024-11-01',

  sentry: {
    org: 'hack-softwares',
    project: 'chatly-frontend',
  },

  sourcemap: {
    client: 'hidden',
  },
})