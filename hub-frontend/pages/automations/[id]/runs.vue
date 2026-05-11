<script setup lang="ts">
import { Icon } from '@iconify/vue'

useHead({ title: 'Histórico de execuções' })

const route = useRoute()
const api = useApi()
const automationId = Number(route.params.id)

interface Run {
  id: number
  status: 'running' | 'completed' | 'failed'
  context: Record<string, any>
  current_step: number
  error: string
  started_at: string
  finished_at: string | null
}

const runs = ref<Run[]>([])
const automationName = ref('')
const loading = ref(true)

const statusColor = (s: string) => ({
  completed: 'text-green-400 border-green-400/30',
  failed: 'text-red-400 border-red-400/30',
  running: 'text-yellow-400 border-yellow-400/30',
}[s] || 'text-neutral-400 border-white/10')

const fmt = (iso: string | null) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('pt-BR')
}

const fetchAll = async () => {
  try {
    const [runsList, auto] = await Promise.all([
      api<Run[]>(`/api/automations/${automationId}/runs/`),
      api<{ name: string }>(`/api/automations/${automationId}/`),
    ])
    runs.value = runsList
    automationName.value = auto.name
  } finally {
    loading.value = false
  }
}

onMounted(fetchAll)
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 md:px-8 py-8">
    <div class="mb-6 flex items-center gap-3">
      <NuxtLink :to="`/automations/${automationId}`" class="text-neutral-500 hover:text-neutral-300">
        <Icon icon="solar:arrow-left-bold-duotone" class="text-lg" />
      </NuxtLink>
      <div>
        <p class="field-label mb-0.5">{{ automationName }}</p>
        <h1 class="text-xl font-medium text-white tracking-tight">Execuções</h1>
      </div>
    </div>

    <div v-if="loading" class="space-y-2">
      <div v-for="i in 5" :key="i" class="h-16 bg-white/5 animate-pulse"></div>
    </div>

    <div v-else-if="runs.length === 0" class="flex flex-col items-center justify-center py-16 border border-white/5 text-center">
      <Icon icon="solar:history-bold-duotone" class="text-4xl text-white/10 mb-3" />
      <p class="text-xs font-mono text-neutral-700">Nenhuma execução registrada.</p>
    </div>

    <div v-else class="space-y-px">
      <div v-for="r in runs" :key="r.id" class="bg-surface border border-white/5 px-5 py-4">
        <div class="flex items-center justify-between gap-3 mb-2">
          <div class="flex items-center gap-3">
            <span class="text-[10px] font-mono text-neutral-600 uppercase">#{{ r.id }}</span>
            <span
              class="text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 border"
              :class="statusColor(r.status)"
            >{{ r.status }}</span>
            <span class="text-[10px] font-mono text-neutral-600">passo {{ r.current_step }}</span>
          </div>
          <span class="text-[10px] font-mono text-neutral-700">{{ fmt(r.started_at) }}</span>
        </div>

        <div v-if="r.error" class="bg-red-500/5 border border-red-500/20 px-3 py-2 mt-2">
          <p class="text-[10px] font-mono text-red-400 break-all">{{ r.error }}</p>
        </div>

        <details v-if="Object.keys(r.context || {}).length" class="mt-2">
          <summary class="text-[10px] font-mono text-neutral-600 uppercase tracking-widest cursor-pointer hover:text-neutral-400">contexto</summary>
          <pre class="text-[10px] font-mono text-neutral-500 mt-2 overflow-x-auto">{{ JSON.stringify(r.context, null, 2) }}</pre>
        </details>
      </div>
    </div>
  </div>
</template>
