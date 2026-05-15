<script setup lang="ts">
useHead({
  bodyAttrs: { class: '!overflow-y-auto' },
})

const authStore = useAuthStore()
const mobileOpen = ref(false)

// Login/registro/painel vivem no domínio da aplicação (app.*).
// Em dev appUrl é vazio → links relativos no mesmo host.
const appUrl = useRuntimeConfig().public.appUrl
const appLink = (path: string) => `${appUrl}${path}`
</script>

<template>
  <div class="min-h-screen bg-canvas relative">
    <!-- Grid background -->
    <div class="fixed inset-0 grid-bg pointer-events-none z-0"></div>

    <!-- Header -->
    <header class="sticky top-0 z-30 border-b border-white/5 bg-canvas/80 backdrop-blur-md">
      <div class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <NuxtLink to="/" class="flex items-center gap-2">
          <div class="w-3 h-3 bg-accent"></div>
          <span class="text-white text-xs font-mono uppercase tracking-widest">ChatlyAi</span>
        </NuxtLink>

        <!-- Nav desktop -->
        <nav class="hidden md:flex items-center gap-8">
          <a href="/#recursos" class="text-xs font-mono uppercase tracking-widest text-neutral-400 hover:text-white transition-colors">Recursos</a>
          <a href="/#como-funciona" class="text-xs font-mono uppercase tracking-widest text-neutral-400 hover:text-white transition-colors">Como funciona</a>
          <template v-if="authStore.isAuthenticated">
            <a :href="appLink('/dashboard')" class="text-xs font-mono uppercase tracking-widest text-accent hover:text-white transition-colors">
              Ir ao painel →
            </a>
          </template>
          <template v-else>
            <a :href="appLink('/login')" class="text-xs font-mono uppercase tracking-widest text-neutral-400 hover:text-white transition-colors">Entrar</a>
            <a
              :href="appLink('/register')"
              class="relative inline-flex items-center px-5 py-2.5 border border-white/10 hover:border-accent transition-colors"
            >
              <span class="text-white text-xs font-medium uppercase tracking-wider">Começar agora</span>
            </a>
          </template>
        </nav>

        <!-- Toggle mobile -->
        <button class="md:hidden text-neutral-300" @click="mobileOpen = !mobileOpen" aria-label="Menu">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="!mobileOpen" d="M3 6h18M3 12h18M3 18h18" />
            <path v-else d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>

      <!-- Nav mobile -->
      <div v-if="mobileOpen" class="md:hidden border-t border-white/5 px-6 py-4 flex flex-col gap-4 bg-canvas">
        <a href="/#recursos" class="text-xs font-mono uppercase tracking-widest text-neutral-400" @click="mobileOpen = false">Recursos</a>
        <a href="/#como-funciona" class="text-xs font-mono uppercase tracking-widest text-neutral-400" @click="mobileOpen = false">Como funciona</a>
        <a v-if="authStore.isAuthenticated" :href="appLink('/dashboard')" class="text-xs font-mono uppercase tracking-widest text-accent">Ir ao painel →</a>
        <template v-else>
          <a :href="appLink('/login')" class="text-xs font-mono uppercase tracking-widest text-neutral-400">Entrar</a>
          <a :href="appLink('/register')" class="text-xs font-mono uppercase tracking-widest text-accent">Começar agora →</a>
        </template>
      </div>
    </header>

    <!-- Content -->
    <main class="relative z-10">
      <slot />
    </main>

    <!-- Footer -->
    <footer class="relative z-10 border-t border-white/5 mt-24">
      <div class="max-w-6xl mx-auto px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4">
        <div class="flex items-center gap-2">
          <div class="w-2.5 h-2.5 bg-accent"></div>
          <span class="text-white text-xs font-mono uppercase tracking-widest">ChatlyAi</span>
        </div>
        <nav class="flex items-center gap-6">
          <NuxtLink to="/privacidade" class="text-xs font-mono text-neutral-500 hover:text-white transition-colors">Privacidade</NuxtLink>
          <NuxtLink to="/cookies" class="text-xs font-mono text-neutral-500 hover:text-white transition-colors">Cookies</NuxtLink>
          <a :href="appLink('/login')" class="text-xs font-mono text-neutral-500 hover:text-white transition-colors">Entrar</a>
        </nav>
        <p class="text-xs font-mono text-neutral-600">© {{ new Date().getFullYear() }} Hack Softwares</p>
      </div>
    </footer>
  </div>
</template>
