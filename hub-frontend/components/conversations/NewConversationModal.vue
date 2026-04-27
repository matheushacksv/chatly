<script setup lang="ts">
import { Icon } from '@iconify/vue'

const props = defineProps<{
  open: boolean
  activeConversations: any[]
}>()
const emit = defineEmits<{ close: []; created: [conv: any] }>()

const api = useApi()

// ---- Modo ----
const mode = ref<'existing' | 'new'>('existing')

// ---- Contatos existentes ----
const contacts = ref<any[]>([])
const contactSearch = ref('')
const selectedContact = ref<any>(null)
const contactsLoading = ref(false)

const activePhonesSet = computed(() =>
  new Set(props.activeConversations.filter(c => c.status === 'open').map(c => c.contact?.phone))
)

const filteredContacts = computed(() => {
  const q = contactSearch.value.trim().toLowerCase()
  return contacts.value
    .filter(c => !activePhonesSet.value.has(c.phone))
    .filter(c =>
      !q ||
      c.name?.toLowerCase().includes(q) ||
      c.phone?.includes(q)
    )
})

// ---- Formulário compartilhado ----
const form = reactive({
  phone: '',
  name: '',
  instance_id: null as number | null,
  agent_id: null as number | null,
  message: '',
})

const instances = ref<any[]>([])
const agents = ref<any[]>([])
const loading = ref(false)
const error = ref('')

watch(() => props.open, async (val) => {
  if (!val) return
  // reset
  mode.value = 'existing'
  error.value = ''
  contactSearch.value = ''
  selectedContact.value = null
  form.phone = ''
  form.name = ''
  form.message = ''
  form.instance_id = null
  form.agent_id = null

  contactsLoading.value = true
  try {
    ;[instances.value, agents.value, contacts.value] = await Promise.all([
      api<any[]>('/api/integrations/whatsapp/'),
      api<any[]>('/api/agents/'),
      api<any[]>('/api/contacts/'),
    ])
    const connected = instances.value.filter(i => i.status === 'connected')
    if (connected.length > 0) form.instance_id = connected[0].id
  } catch {}
  finally { contactsLoading.value = false }
})

const selectContact = (contact: any) => {
  selectedContact.value = contact
  form.phone = contact.phone
  form.name = contact.name || ''
}

const submit = async () => {
  if (!form.phone.trim() || !form.instance_id) return
  loading.value = true
  error.value = ''
  try {
    const conv = await api<any>('/api/conversations/start/', {
      method: 'POST',
      body: {
        phone: form.phone.trim(),
        name: form.name.trim(),
        instance_id: form.instance_id,
        agent_id: form.agent_id,
        message: form.message.trim(),
      },
    })
    emit('created', conv)
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao iniciar conversa'
  } finally {
    loading.value = false
  }
}

const canSubmit = computed(() => {
  if (!form.instance_id) return false
  if (mode.value === 'existing') return !!selectedContact.value
  return !!form.phone.trim()
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="emit('close')"></div>

        <div class="relative bg-surface border border-white/10 w-full max-w-md z-10">
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <div class="px-8 pt-8 pb-2">
            <p class="field-label mb-1">Conversas</p>
            <h2 class="text-xl font-medium text-white tracking-tight">Nova conversa</h2>
          </div>

          <!-- Tabs modo -->
          <div class="flex border-b border-white/5 px-8 mt-5">
            <button
              @click="mode = 'existing'; selectedContact = null"
              class="pb-2.5 mr-6 text-[10px] font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors"
              :class="mode === 'existing' ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
            >
              Contato existente
            </button>
            <button
              @click="mode = 'new'; selectedContact = null; form.phone = ''; form.name = ''"
              class="pb-2.5 text-[10px] font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors"
              :class="mode === 'new' ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
            >
              Novo contato
            </button>
          </div>

          <form @submit.prevent="submit" class="px-8 py-6 space-y-4">

            <!-- ===== MODO: CONTATO EXISTENTE ===== -->
            <template v-if="mode === 'existing'">
              <!-- Contato selecionado -->
              <div v-if="selectedContact" class="flex items-center gap-3 px-4 py-3 bg-accent/5 border border-accent/30">
                <div class="w-7 h-7 bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
                  <span class="text-[10px] font-mono text-accent uppercase">{{ selectedContact.name?.[0] || '?' }}</span>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-white font-medium truncate">{{ selectedContact.name }}</p>
                  <p class="text-[11px] font-mono text-neutral-500">{{ selectedContact.phone }}</p>
                </div>
                <button type="button" @click="selectedContact = null; form.phone = ''; form.name = ''" class="text-neutral-400 hover:text-white transition-colors">
                  <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
                </button>
              </div>

              <!-- Busca + lista de contatos -->
              <div v-else>
                <div class="flex items-center border border-white/10 focus-within:border-accent/50 bg-canvas px-3 gap-2 mb-2">
                  <Icon icon="solar:magnifer-bold-duotone" class="text-neutral-600 text-sm shrink-0" />
                  <input
                    v-model="contactSearch"
                    type="text"
                    placeholder="Buscar por nome ou telefone..."
                    class="flex-1 bg-transparent py-2.5 text-sm text-white font-mono outline-none placeholder-neutral-700"
                  />
                </div>

                <div class="max-h-44 overflow-y-auto border border-white/5 bg-canvas">
                  <div v-if="contactsLoading" class="flex items-center justify-center py-8">
                    <Icon icon="solar:refresh-bold-duotone" class="text-neutral-600 text-lg animate-spin" />
                  </div>
                  <div v-else-if="filteredContacts.length === 0" class="flex flex-col items-center justify-center py-8 text-center">
                    <Icon icon="solar:users-group-rounded-bold-duotone" class="text-2xl text-white/10 mb-2" />
                    <p class="text-xs font-mono text-neutral-700">
                      {{ contacts.length === 0 ? 'Nenhum contato cadastrado' : 'Todos os contatos já têm conversa ativa' }}
                    </p>
                  </div>
                  <button
                    v-for="contact in filteredContacts"
                    :key="contact.id"
                    type="button"
                    @click="selectContact(contact)"
                    class="w-full flex items-center gap-3 px-3 py-2.5 text-left border-b border-white/[0.03] last:border-0 hover:bg-white/[0.03] transition-colors"
                  >
                    <div class="w-6 h-6 bg-neutral-900 border border-white/10 flex items-center justify-center shrink-0">
                      <span class="text-[9px] font-mono text-neutral-400 uppercase">{{ contact.name?.[0] || '?' }}</span>
                    </div>
                    <div class="flex-1 min-w-0">
                      <p class="text-xs text-white font-medium truncate">{{ contact.name }}</p>
                      <p class="text-[10px] font-mono text-neutral-600">{{ contact.phone }}</p>
                    </div>
                  </button>
                </div>
              </div>
            </template>

            <!-- ===== MODO: NOVO CONTATO ===== -->
            <template v-else>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="field-label">Telefone <span class="text-red-500">*</span></label>
                  <div class="input-wrapper">
                    <input v-model="form.phone" type="text" placeholder="5511999999999" required class="input-field" />
                  </div>
                  <p class="text-[10px] font-mono text-neutral-700 mt-1 pl-4">DDI + DDD + número</p>
                </div>
                <div>
                  <label class="field-label">Nome <span class="text-neutral-700 normal-case">(opcional)</span></label>
                  <div class="input-wrapper">
                    <input v-model="form.name" type="text" placeholder="João Silva" class="input-field" />
                  </div>
                </div>
              </div>
            </template>

            <!-- ===== CAMPOS COMUNS ===== -->

            <!-- Instância -->
            <div>
              <label class="field-label">Instância WhatsApp <span class="text-red-500">*</span></label>
              <div class="bg-surface border border-white/10 rounded-full py-3 pl-6 pr-4 hover:border-accent/50 transition-colors">
                <select
                  v-model="form.instance_id"
                  required
                  class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer"
                >
                  <option :value="null" class="bg-surface text-neutral-500">Selecionar instância</option>
                  <option
                    v-for="inst in instances.filter(i => i.status === 'connected')"
                    :key="inst.id"
                    :value="inst.id"
                    class="bg-surface text-white"
                  >
                    {{ inst.instance_name }}
                  </option>
                </select>
              </div>
              <p v-if="instances.filter(i => i.status === 'connected').length === 0" class="text-[10px] font-mono text-yellow-500 mt-1 pl-4">
                Nenhuma instância conectada
              </p>
            </div>

            <!-- Agente -->
            <div>
              <label class="field-label">Agente de IA <span class="text-neutral-700 normal-case">(opcional)</span></label>
              <div class="bg-surface border border-white/10 rounded-full py-3 pl-6 pr-4 hover:border-accent/50 transition-colors">
                <select
                  v-model="form.agent_id"
                  class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer"
                >
                  <option :value="null" class="bg-surface text-neutral-500">Sem agente</option>
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

            <!-- Mensagem inicial -->
            <div>
              <label class="field-label">Mensagem inicial <span class="text-neutral-700 normal-case">(opcional)</span></label>
              <div class="bg-canvas border border-white/10 hover:border-accent/50 transition-colors">
                <textarea
                  v-model="form.message"
                  rows="3"
                  placeholder="Olá! Como posso te ajudar?"
                  class="w-full bg-transparent px-5 py-3 text-sm text-white font-mono placeholder-neutral-700 outline-none resize-none leading-relaxed"
                ></textarea>
              </div>
            </div>

            <p v-if="error" class="text-xs font-mono text-red-400">{{ error }}</p>

            <div class="flex gap-3 pt-1">
              <button
                type="button"
                @click="emit('close')"
                class="flex-1 py-3 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                :disabled="loading || !canSubmit"
                class="btn-primary flex-1 disabled:opacity-50"
              >
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">
                  {{ loading ? 'Iniciando...' : 'Iniciar' }}
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
