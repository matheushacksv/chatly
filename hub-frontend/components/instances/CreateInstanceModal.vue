<script setup lang="ts">
const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; created: [instance: any] }>()

const api = useApi()

const form = reactive({ name: '', agent_id: null as number | null })
const agents = ref<any[]>([])
const loading = ref(false)
const error = ref('')

watch(() => props.open, async (val) => {
  if (val) {
    error.value = ''
    form.name = ''
    form.agent_id = null
    try {
      agents.value = await api<any[]>('/api/agents/')
    } catch {}
  }
})

const submit = async () => {
  if (!form.name.trim()) return
  loading.value = true
  error.value = ''
  try {
    const instance = await api<any>('/api/integrations/whatsapp/', {
      method: 'POST',
      body: { name: form.name, agent_id: form.agent_id },
    })
    emit('created', instance)
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao criar instância'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <!-- Overlay -->
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="emit('close')"></div>

        <!-- Modal -->
        <div class="relative bg-surface border border-white/10 w-full max-w-md p-8 z-10">
          <!-- Corner accents -->
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <p class="field-label mb-1">WhatsApp</p>
          <h2 class="text-xl font-medium text-white mb-8 tracking-tight">Nova instância</h2>

          <form @submit.prevent="submit" class="space-y-5">
            <!-- Nome -->
            <div>
              <label class="field-label">Nome da instância</label>
              <div class="input-wrapper">
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="minha-empresa-01"
                  required
                  class="input-field"
                />
              </div>
            </div>

            <!-- Agente (opcional) -->
            <div>
              <label class="field-label">Agente de IA <span class="text-neutral-700 normal-case">(opcional)</span></label>
              <div class="bg-surface border border-white/10 rounded-full py-3 pl-6 pr-4 hover:border-accent/50 transition-colors">
                <select
                  v-model="form.agent_id"
                  class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer"
                >
                  <option :value="null" class="bg-surface text-neutral-400">Sem agente</option>
                  <option
                    v-for="agent in agents"
                    :key="agent.id"
                    :value="agent.id"
                    class="bg-surface text-white"
                  >
                    {{ agent.name }}
                  </option>
                </select>
              </div>
            </div>

            <p v-if="error" class="text-xs font-mono text-red-400">{{ error }}</p>

            <!-- Actions -->
            <div class="flex gap-3 pt-2">
              <button
                type="button"
                @click="emit('close')"
                class="flex-1 py-3 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                :disabled="loading"
                class="btn-primary flex-1 disabled:opacity-50"
              >
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">
                  {{ loading ? 'Criando...' : 'Criar' }}
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
