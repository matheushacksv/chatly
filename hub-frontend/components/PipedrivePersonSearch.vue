<script setup lang="ts">
import { Icon } from '@iconify/vue'

const emit = defineEmits<{ select: [person: any] }>()
const api = useApi()

const term = ref('')
const results = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const searched = ref(false)

let timer: any = null

watch(term, (q) => {
  clearTimeout(timer)
  error.value = ''
  const query = q.trim()
  if (query.length < 2) {
    results.value = []
    loading.value = false
    searched.value = false
    return
  }
  loading.value = true
  timer = setTimeout(async () => {
    try {
      results.value = await api<any[]>('/api/org/integrations/pipedrive/persons', {
        query: { q: query },
      })
      searched.value = true
    } catch (e: any) {
      error.value = e?.data?.detail || 'Erro ao buscar no Pipedrive'
      results.value = []
    } finally {
      loading.value = false
    }
  }, 350)
})

onUnmounted(() => clearTimeout(timer))
</script>

<template>
  <div>
    <div class="flex items-center border border-white/10 focus-within:border-accent/50 bg-canvas px-3 gap-2 mb-2">
      <Icon icon="solar:magnifer-bold-duotone" class="text-neutral-600 text-sm shrink-0" />
      <input
        v-model="term"
        type="text"
        placeholder="Buscar no Pipedrive por nome ou telefone..."
        class="flex-1 bg-transparent py-2.5 text-sm text-white font-mono outline-none placeholder-neutral-700"
      />
    </div>

    <p v-if="error" class="text-[10px] font-mono text-yellow-500 mb-2 pl-1">{{ error }}</p>

    <div class="max-h-44 overflow-y-auto border border-white/5 bg-canvas">
      <div v-if="loading" class="flex items-center justify-center py-8">
        <Icon icon="solar:refresh-bold-duotone" class="text-neutral-600 text-lg animate-spin" />
      </div>
      <div v-else-if="term.trim().length < 2" class="flex flex-col items-center justify-center py-8 text-center">
        <Icon icon="solar:database-bold-duotone" class="text-2xl text-white/10 mb-2" />
        <p class="text-xs font-mono text-neutral-700">Digite ao menos 2 caracteres</p>
      </div>
      <div v-else-if="results.length === 0 && searched" class="flex flex-col items-center justify-center py-8 text-center">
        <Icon icon="solar:user-cross-bold-duotone" class="text-2xl text-white/10 mb-2" />
        <p class="text-xs font-mono text-neutral-700">Nenhuma pessoa encontrada</p>
      </div>
      <button
        v-for="person in results"
        :key="person.pipedrive_person_id"
        type="button"
        @click="emit('select', person)"
        class="w-full flex items-center gap-3 px-3 py-2.5 text-left border-b border-white/[0.03] last:border-0 hover:bg-white/[0.03] transition-colors"
      >
        <div class="w-6 h-6 bg-neutral-900 border border-white/10 flex items-center justify-center shrink-0">
          <span class="text-[9px] font-mono text-neutral-400 uppercase">{{ person.name?.[0] || '?' }}</span>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs text-white font-medium truncate">{{ person.name || 'Sem nome' }}</p>
          <p class="text-[10px] font-mono text-neutral-600">{{ person.phone || person.email || '—' }}</p>
        </div>
      </button>
    </div>
  </div>
</template>
