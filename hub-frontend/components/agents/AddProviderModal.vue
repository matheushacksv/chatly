<script setup lang="ts">
const props = defineProps<{ open: boolean; providerType: string }>()
const emit = defineEmits<{ close: []; added: [provider: any] }>()

const api = useApi()
const apiKey = ref('')
const loading = ref(false)
const error = ref('')

const LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  groq: 'Groq',
}

watch(() => props.open, (val) => {
  if (val) { apiKey.value = ''; error.value = '' }
})

const submit = async () => {
  if (!apiKey.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const provider = await api<any>('/api/agents/providers', {
      method: 'POST',
      body: { provider_type: props.providerType, api_key: apiKey.value.trim() },
    })
    emit('added', provider)
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao adicionar provedor'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="emit('close')"></div>

        <div class="relative bg-surface border border-white/10 w-full max-w-md p-8 z-10">
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <p class="field-label mb-1">Provedor</p>
          <h2 class="text-xl font-medium text-white mb-8 tracking-tight">
            Configurar {{ LABELS[providerType] ?? providerType }}
          </h2>

          <form @submit.prevent="submit" class="space-y-5">
            <div>
              <label class="field-label">Chave de API</label>
              <div class="input-wrapper">
                <input
                  v-model="apiKey"
                  type="password"
                  placeholder="sk-..."
                  required
                  class="input-field"
                />
              </div>
              <p class="text-[11px] font-mono text-neutral-600 mt-1.5 pl-4">
                Armazenada com segurança — não pode ser visualizada após salvar
              </p>
            </div>

            <p v-if="error" class="text-xs font-mono text-red-400">{{ error }}</p>

            <div class="flex gap-3 pt-2">
              <button
                type="button"
                @click="emit('close')"
                class="flex-1 py-3 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors"
              >
                Cancelar
              </button>
              <button type="submit" :disabled="loading" class="btn-primary flex-1 disabled:opacity-50">
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">
                  {{ loading ? 'Salvando...' : 'Salvar' }}
                </span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
