<script setup lang="ts">
import { Icon } from '@iconify/vue'

const props = defineProps<{
  page: number
  totalPages: number
  compact?: boolean   // sidebar / espaço reduzido
}>()

const emit = defineEmits<{
  prev: []
  next: []
  goTo: [page: number]
}>()

// Gera os números de página visíveis com reticências quando necessário
const visiblePages = computed(() => {
  const total = props.totalPages
  const cur = props.page

  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)

  const pages: (number | '…')[] = []

  // Sempre mostra primeira e última
  // Janela de ±2 ao redor da página atual
  const left  = Math.max(2, cur - 1)
  const right = Math.min(total - 1, cur + 1)

  pages.push(1)
  if (left > 2) pages.push('…')
  for (let i = left; i <= right; i++) pages.push(i)
  if (right < total - 1) pages.push('…')
  pages.push(total)

  return pages
})
</script>

<template>
  <!-- Modo compacto (sidebar) -->
  <div v-if="compact" class="flex items-center justify-between px-4 py-2.5 border-t border-white/5 shrink-0">
    <button
      @click="emit('prev')"
      :disabled="page <= 1"
      class="p-1 text-neutral-600 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
    >
      <Icon icon="solar:arrow-left-bold-duotone" class="text-sm" />
    </button>
    <span class="text-[10px] font-mono text-neutral-600">
      {{ page }} / {{ totalPages }}
    </span>
    <button
      @click="emit('next')"
      :disabled="page >= totalPages"
      class="p-1 text-neutral-600 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
    >
      <Icon icon="solar:arrow-right-bold-duotone" class="text-sm" />
    </button>
  </div>

  <!-- Modo normal (página inteira) -->
  <div v-else class="flex items-center justify-center gap-1 mt-6">
    <button
      @click="emit('prev')"
      :disabled="page <= 1"
      class="flex items-center gap-1 px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-white/5 text-neutral-500 hover:border-white/15 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
    >
      <Icon icon="solar:arrow-left-bold-duotone" class="text-xs" />
      Anterior
    </button>

    <template v-for="p in visiblePages" :key="String(p) + '_' + page">
      <span v-if="p === '…'" class="px-2 text-xs font-mono text-neutral-700 select-none">…</span>
      <button
        v-else
        @click="p !== page && emit('goTo', p as number)"
        class="w-8 h-8 text-[11px] font-mono border transition-colors"
        :class="p === page
          ? 'border-accent/50 text-accent bg-accent/5'
          : 'border-white/5 text-neutral-500 hover:border-white/15 hover:text-neutral-300'"
      >
        {{ p }}
      </button>
    </template>

    <button
      @click="emit('next')"
      :disabled="page >= totalPages"
      class="flex items-center gap-1 px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-white/5 text-neutral-500 hover:border-white/15 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
    >
      Próximo
      <Icon icon="solar:arrow-right-bold-duotone" class="text-xs" />
    </button>
  </div>
</template>
