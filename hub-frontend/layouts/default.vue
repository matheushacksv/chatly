<script setup lang="ts">
import { Icon } from '@iconify/vue'

const authStore = useAuthStore()
const { toggle, isCollapsed } = useSidebar()
const { connect, disconnect } = useOrgWs()

onMounted(async () => {
  if (authStore.accessToken && !authStore.user) {
    await authStore.fetchMe(true)
  }
  connect()
})

onUnmounted(() => disconnect())
</script>

<template>
  <div class="h-screen bg-canvas flex overflow-hidden">
    <AppSidebar />
    <AppConfirmModal />
    <main class="flex-1 flex flex-col h-screen overflow-hidden transition-all duration-200" :class="isCollapsed ? 'ml-0 md:ml-14' : 'ml-0 md:ml-56'">
      <!-- Barra mobile com hamburger -->
      <div class="md:hidden h-12 shrink-0 bg-surface border-b border-white/5 flex items-center px-4 gap-3 z-10">
        <button
          @click="toggle"
          class="w-7 h-7 flex items-center justify-center text-neutral-400 hover:text-white transition-colors"
          aria-label="Menu"
        >
          <Icon icon="solar:hamburger-menu-bold-duotone" class="text-base" />
        </button>
        <span class="text-[10px] font-mono uppercase tracking-widest text-neutral-600">ChatlyAi</span>
      </div>
      <!-- Conteúdo -->
      <div class="flex-1 min-h-0 overflow-auto">
        <slot />
      </div>
    </main>
  </div>
</template>
