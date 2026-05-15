<script setup lang="ts">
const { hasDecided, accept, reject } = useCookieConsent()

// Evita flash no SSR — só renderiza depois de montar no cliente
const mounted = ref(false)
onMounted(() => {
  mounted.value = true
})

const visible = computed(() => mounted.value && !hasDecided.value)
</script>

<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="translate-y-full opacity-0"
    enter-to-class="translate-y-0 opacity-100"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="translate-y-0 opacity-100"
    leave-to-class="translate-y-full opacity-0"
  >
    <div
      v-if="visible"
      class="fixed bottom-0 inset-x-0 z-[100] p-4 sm:p-6"
    >
      <div
        class="max-w-3xl mx-auto bg-surface border border-white/10 p-5 flex flex-col sm:flex-row sm:items-center gap-4"
      >
        <p class="text-sm text-neutral-400 leading-relaxed flex-1">
          Usamos cookies para manter sua sessão e melhorar a experiência. Veja a
          <NuxtLink to="/cookies" class="text-accent hover:text-white transition-colors">
            política de cookies</NuxtLink>.
        </p>
        <div class="flex items-center gap-3 shrink-0">
          <button
            class="px-4 py-2 text-xs font-mono uppercase tracking-wider text-neutral-400 hover:text-white transition-colors"
            @click="reject"
          >
            Recusar
          </button>
          <button
            class="px-5 py-2.5 border border-white/10 hover:border-accent transition-colors text-xs font-medium uppercase tracking-wider text-white"
            @click="accept"
          >
            Aceitar
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>
