<script setup lang="ts">
import { Icon } from '@iconify/vue'

const route = useRoute()
const router = useRouter()
const api = useApi()
const { confirm: confirmDialog } = useConfirm()
const labelsStore = useLabelsStore()

const campaignId = computed(() => Number(route.params.id))

const campaign = ref<any>(null)
const contacts = ref<any[]>([])
const loading = ref(true)
const saving = ref(false)
const actionError = ref('')

const fetchAll = async () => {
  try {
    ;[campaign.value, contacts.value] = await Promise.all([
      api<any>(`/api/campaigns/${campaignId.value}/`),
      api<any[]>(`/api/campaigns/${campaignId.value}/contacts/`),
    ])
  } catch {
    router.push('/campaigns')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  labelsStore.fetchLabels()
  fetchAll()
})

// Polling when running
let pollTimer: ReturnType<typeof setInterval> | null = null

watch(() => campaign.value?.status, (status) => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (status === 'running') {
    pollTimer = setInterval(async () => {
      try {
        ;[campaign.value, contacts.value] = await Promise.all([
          api<any>(`/api/campaigns/${campaignId.value}/`),
          api<any[]>(`/api/campaigns/${campaignId.value}/contacts/`),
        ])
      } catch {}
      if (campaign.value?.status !== 'running') {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
      }
    }, 5000)
  }
}, { immediate: true })

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })

// Status config
const statusConfig: Record<string, { label: string; cls: string }> = {
  draft:     { label: 'Rascunho',  cls: 'text-neutral-400 border-white/10 bg-white/5' },
  running:   { label: 'Enviando',  cls: 'text-accent border-accent/30 bg-accent/5' },
  paused:    { label: 'Pausada',   cls: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/5' },
  finished:  { label: 'Concluída', cls: 'text-green-400 border-green-500/30 bg-green-500/5' },
  cancelled: { label: 'Cancelada', cls: 'text-red-400 border-red-500/30 bg-red-500/5' },
}

const contactStatusConfig: Record<string, { label: string; cls: string }> = {
  pending:  { label: 'Aguardando', cls: 'text-neutral-400' },
  sent:     { label: 'Enviado',    cls: 'text-green-400' },
  failed:   { label: 'Falhou',     cls: 'text-red-400' },
  skipped:  { label: 'Ignorado',   cls: 'text-neutral-600' },
}

const progressPercent = computed(() => {
  if (!campaign.value?.total_contacts) return 0
  return Math.round(((campaign.value.sent_count + campaign.value.failed_count) / campaign.value.total_contacts) * 100)
})

const pendingCount = computed(() => contacts.value.filter(c => c.status === 'pending').length)

// Actions
const doAction = async (action: 'start' | 'pause' | 'resume' | 'cancel') => {
  const messages: Record<string, { title: string; body: string }> = {
    start:  { title: 'Iniciar campanha',   body: `Enviar para ${campaign.value?.total_contacts} contato(s)?` },
    cancel: { title: 'Cancelar campanha',  body: 'Contatos pendentes não receberão mensagem.' },
  }
  if (messages[action]) {
    const ok = await confirmDialog(messages[action].body, { title: messages[action].title })
    if (!ok) return
  }
  saving.value = true
  actionError.value = ''
  try {
    campaign.value = await api<any>(`/api/campaigns/${campaignId.value}/${action}/`, { method: 'POST' })
  } catch (e: any) {
    actionError.value = e?.data?.detail || 'Erro ao executar ação'
  } finally {
    saving.value = false
  }
}

// Add contacts modal
const addModal = ref(false)
const addTab = ref<'label' | 'manual' | 'all'>('label')
const selectedLabelIds = ref<number[]>([])
const selectedContactIds = ref<number[]>([])
const allContacts = ref<any[]>([])
const contactSearch = ref('')
const addingContacts = ref(false)
const allContactsLoaded = ref(false)
const addError = ref('')

const filteredContacts = computed(() => {
  const q = contactSearch.value.toLowerCase().trim()
  const existing = new Set(contacts.value.map(cc => cc.contact_id))
  const list = allContacts.value.filter(c => !existing.has(c.id))
  if (!q) return list
  return list.filter(c => c.name?.toLowerCase().includes(q) || c.phone?.includes(q))
})

const openAddModal = async () => {
  selectedLabelIds.value = []
  selectedContactIds.value = []
  contactSearch.value = ''
  addError.value = ''
  addTab.value = 'label'
  addModal.value = true
  if (!allContactsLoaded.value) {
    try {
      allContacts.value = await api<any[]>('/api/contacts/')
      allContactsLoaded.value = true
    } catch {}
  }
}

const toggleLabel = (id: number) => {
  const idx = selectedLabelIds.value.indexOf(id)
  if (idx === -1) selectedLabelIds.value.push(id)
  else selectedLabelIds.value.splice(idx, 1)
}

const toggleContact = (id: number) => {
  const idx = selectedContactIds.value.indexOf(id)
  if (idx === -1) selectedContactIds.value.push(id)
  else selectedContactIds.value.splice(idx, 1)
}

const doAddContacts = async () => {
  addError.value = ''
  if (addTab.value === 'manual' && !selectedContactIds.value.length) {
    addError.value = 'Selecione ao menos um contato'
    return
  }
  if (addTab.value === 'label' && !selectedLabelIds.value.length) {
    addError.value = 'Selecione ao menos uma etiqueta'
    return
  }
  addingContacts.value = true
  try {
    campaign.value = await api<any>(`/api/campaigns/${campaignId.value}/contacts/`, {
      method: 'POST',
      body: {
        contact_ids: addTab.value === 'manual' ? selectedContactIds.value : [],
        label_ids: addTab.value === 'label' ? selectedLabelIds.value : [],
        add_all: addTab.value === 'all',
      },
    })
    contacts.value = await api<any[]>(`/api/campaigns/${campaignId.value}/contacts/`)
    addModal.value = false
  } catch (e: any) {
    addError.value = e?.data?.detail || 'Erro ao adicionar contatos'
  } finally {
    addingContacts.value = false
  }
}

const removeContact = async (cc: any) => {
  try {
    await api(`/api/campaigns/${campaignId.value}/contacts/${cc.id}/`, { method: 'DELETE' })
    contacts.value = contacts.value.filter(c => c.id !== cc.id)
    if (campaign.value) campaign.value.total_contacts = Math.max(0, campaign.value.total_contacts - 1)
  } catch {}
}

const formatDate = (d: string | null) => {
  if (!d) return '—'
  return new Date(d).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="min-h-screen bg-canvas p-6">
    <div class="max-w-4xl mx-auto space-y-6">

      <!-- Loading -->
      <div v-if="loading" class="space-y-4">
        <div class="h-8 bg-white/5 animate-pulse w-1/2" />
        <div class="h-32 bg-white/5 animate-pulse" />
        <div class="h-48 bg-white/5 animate-pulse" />
      </div>

      <template v-else-if="campaign">

        <!-- Header -->
        <div class="flex items-start gap-4">
          <button
            @click="router.push('/campaigns')"
            class="text-neutral-500 hover:text-neutral-300 transition-colors mt-0.5 shrink-0"
          >
            <Icon icon="solar:arrow-left-bold-duotone" class="text-base" />
          </button>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2.5 flex-wrap">
              <h1 class="text-sm font-mono text-white">{{ campaign.name }}</h1>
              <span
                class="px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest border"
                :class="statusConfig[campaign.status]?.cls || statusConfig.draft.cls"
              >{{ statusConfig[campaign.status]?.label || campaign.status }}</span>
            </div>
            <p class="text-[10px] font-mono text-neutral-600 mt-0.5">
              {{ campaign.sent_count }} enviados · {{ campaign.failed_count }} com falha · {{ pendingCount }} pendentes
            </p>
          </div>

          <!-- Botões de ação -->
          <div class="flex items-center gap-2 shrink-0">
            <p v-if="actionError" class="text-[10px] font-mono text-red-400">{{ actionError }}</p>
            <button
              v-if="campaign.status === 'draft'"
              :disabled="saving || !campaign.total_contacts || !campaign.messages?.length"
              @click="doAction('start')"
              class="flex items-center gap-1.5 px-3 py-2 bg-accent text-black text-xs font-mono uppercase tracking-wider disabled:opacity-40 hover:opacity-90 transition-opacity"
            >
              <div v-if="saving" class="w-3 h-3 border border-black/30 border-t-black rounded-full animate-spin" />
              <Icon v-else icon="solar:play-circle-bold-duotone" class="text-sm" />
              Iniciar
            </button>
            <button
              v-if="campaign.status === 'running'"
              :disabled="saving"
              @click="doAction('pause')"
              class="flex items-center gap-1.5 px-3 py-2 border border-yellow-500/30 text-yellow-400 text-xs font-mono uppercase tracking-wider disabled:opacity-40 hover:bg-yellow-500/5 transition-colors"
            >
              <Icon icon="solar:pause-circle-bold-duotone" class="text-sm" />
              Pausar
            </button>
            <button
              v-if="campaign.status === 'paused'"
              :disabled="saving"
              @click="doAction('resume')"
              class="flex items-center gap-1.5 px-3 py-2 border border-accent/30 text-accent text-xs font-mono uppercase tracking-wider disabled:opacity-40 hover:bg-accent/5 transition-colors"
            >
              <Icon icon="solar:play-circle-bold-duotone" class="text-sm" />
              Retomar
            </button>
            <button
              v-if="campaign.status === 'running' || campaign.status === 'paused'"
              :disabled="saving"
              @click="doAction('cancel')"
              class="flex items-center gap-1.5 px-3 py-2 border border-red-500/30 text-red-400 text-xs font-mono uppercase tracking-wider disabled:opacity-40 hover:bg-red-500/5 transition-colors"
            >
              <Icon icon="solar:close-circle-bold-duotone" class="text-sm" />
              Cancelar
            </button>
          </div>
        </div>

        <!-- Progresso (quando não draft) -->
        <div v-if="campaign.status !== 'draft' && campaign.total_contacts > 0" class="border border-white/5 bg-surface p-4 space-y-3">
          <div class="flex items-center justify-between">
            <p class="field-label">Progresso</p>
            <span class="text-[10px] font-mono text-neutral-500 tabular-nums">{{ progressPercent }}%</span>
          </div>
          <div class="h-1.5 bg-white/5">
            <div
              class="h-full transition-all duration-500"
              :class="campaign.status === 'finished' ? 'bg-green-500' : campaign.status === 'cancelled' ? 'bg-red-500/50' : 'bg-accent'"
              :style="`width: ${progressPercent}%`"
            />
          </div>
          <div class="flex gap-6 w-full">
            <div class="flex-1">
              <p class="text-[10px] font-mono text-neutral-600">Enviados</p>
              <p class="text-xs font-mono text-green-400 tabular-nums">{{ campaign.sent_count }}</p>
            </div>
            <div class="flex-1">
              <p class="text-[10px] font-mono text-neutral-600">Falhas</p>
              <p class="text-xs font-mono text-red-400 tabular-nums">{{ campaign.failed_count }}</p>
            </div>
            <div class="flex-1">
              <p class="text-[10px] font-mono text-neutral-600">Pendentes</p>
              <p class="text-xs font-mono text-neutral-400 tabular-nums">{{ pendingCount }}</p>
            </div>
            <div class="flex-1">
              <p class="text-[10px] font-mono text-neutral-600">Total</p>
              <p class="text-xs font-mono text-white tabular-nums">{{ campaign.total_contacts }}</p>
            </div>
          </div>
        </div>

        <!-- Configuração -->
        <div class="border border-white/5 bg-surface p-4 space-y-4">
          <p class="field-label">Configuração</p>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <p class="text-[10px] font-mono text-neutral-600 mb-0.5">Instância</p>
              <p class="text-xs font-mono text-white">ID {{ campaign.instance_id }}</p>
            </div>
            <div>
              <p class="text-[10px] font-mono text-neutral-600 mb-0.5">Agente de IA</p>
              <p class="text-xs font-mono" :class="campaign.agent_id ? 'text-white' : 'text-neutral-600'">
                {{ campaign.agent_id ? `ID ${campaign.agent_id}` : 'Nenhum' }}
                <span v-if="campaign.agent_id && campaign.ai_active" class="text-accent ml-1">· IA ativa</span>
              </p>
            </div>
            <div>
              <p class="text-[10px] font-mono text-neutral-600 mb-0.5">Intervalo entre disparos</p>
              <p class="text-xs font-mono text-white">{{ campaign.interval_min }}s — {{ campaign.interval_max }}s</p>
            </div>
            <div>
              <p class="text-[10px] font-mono text-neutral-600 mb-0.5">Criada em</p>
              <p class="text-xs font-mono text-white">{{ formatDate(campaign.created_at) }}</p>
            </div>
          </div>

          <!-- Variantes de mensagem -->
          <div v-if="campaign.messages?.length">
            <p class="text-[10px] font-mono text-neutral-600 mb-2">
              {{ campaign.messages.length }} variante{{ campaign.messages.length > 1 ? 's' : '' }} de mensagem
            </p>
            <div class="space-y-2">
              <div
                v-for="(msg, i) in campaign.messages"
                :key="msg.id"
                class="px-3 py-2.5 border border-white/5 bg-canvas"
              >
                <p v-if="campaign.messages.length > 1" class="text-[9px] font-mono text-neutral-600 uppercase tracking-widest mb-1">Variante {{ i + 1 }}</p>
                <p class="text-xs text-white/80 whitespace-pre-wrap">{{ msg.content }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Contatos -->
        <div class="border border-white/5 bg-surface p-4 space-y-3">
          <div class="flex items-center justify-between">
            <p class="field-label">Contatos <span class="text-neutral-600 font-normal">({{ campaign.total_contacts }})</span></p>
            <button
              v-if="campaign.status === 'draft'"
              @click="openAddModal"
              class="flex items-center gap-1.5 text-xs font-mono text-accent hover:underline"
            >
              <Icon icon="solar:add-circle-bold-duotone" class="text-sm" />
              Adicionar
            </button>
          </div>

          <!-- Empty -->
          <div v-if="!contacts.length" class="py-6 text-center">
            <p class="text-[10px] font-mono text-neutral-700">Nenhum contato adicionado</p>
            <button
              v-if="campaign.status === 'draft'"
              @click="openAddModal"
              class="mt-2 text-[10px] font-mono text-accent hover:underline"
            >Adicionar contatos</button>
          </div>

          <!-- Table -->
          <div v-else class="space-y-0.5">
            <div
              v-for="cc in contacts"
              :key="cc.id"
              class="flex items-center gap-3 px-3 py-2 border border-white/5 group"
            >
              <div class="flex-1 min-w-0">
                <p class="text-xs text-white truncate">{{ cc.contact_name }}</p>
                <p class="text-[10px] font-mono text-neutral-600">{{ cc.contact_phone }}</p>
              </div>
              <span class="text-[10px] font-mono shrink-0" :class="contactStatusConfig[cc.status]?.cls || 'text-neutral-400'">
                {{ contactStatusConfig[cc.status]?.label || cc.status }}
              </span>
              <span v-if="cc.sent_at" class="text-[10px] font-mono text-neutral-600 shrink-0 hidden sm:block">
                {{ formatDate(cc.sent_at) }}
              </span>
              <span v-if="cc.error" :title="cc.error" class="text-[10px] font-mono text-red-400 truncate max-w-24 shrink-0 hidden sm:block">
                {{ cc.error }}
              </span>
              <button
                v-if="campaign.status === 'draft' && cc.status === 'pending'"
                @click="removeContact(cc)"
                class="opacity-0 group-hover:opacity-100 text-neutral-600 hover:text-red-400 transition-all shrink-0"
              >
                <Icon icon="solar:close-circle-bold-duotone" class="text-sm" />
              </button>
            </div>
          </div>
        </div>

      </template>
    </div>
  </div>

  <!-- Modal adicionar contatos -->
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="addModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
        @click.self="addModal = false"
      >
        <div class="bg-surface border border-white/10 w-full max-w-md max-h-[80vh] flex flex-col">

          <!-- Header -->
          <div class="flex items-center justify-between px-5 py-4 border-b border-white/5 shrink-0">
            <p class="text-xs font-mono uppercase tracking-widest text-white">Adicionar Contatos</p>
            <button @click="addModal = false" class="text-neutral-500 hover:text-white transition-colors">
              <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
            </button>
          </div>

          <!-- Tabs -->
          <div class="flex border-b border-white/5 shrink-0">
            <button
              v-for="tab in [{ id: 'label', label: 'Por Etiqueta' }, { id: 'manual', label: 'Manual' }, { id: 'all', label: 'Todos' }]"
              :key="tab.id"
              @click="addTab = tab.id as any"
              class="flex-1 py-2.5 text-[10px] font-mono uppercase tracking-widest transition-colors"
              :class="addTab === tab.id ? 'text-accent border-b border-accent' : 'text-neutral-500 hover:text-neutral-300'"
            >{{ tab.label }}</button>
          </div>

          <!-- Tab content -->
          <div class="flex-1 overflow-y-auto p-4 space-y-2">

            <!-- Por etiqueta -->
            <template v-if="addTab === 'label'">
              <p class="text-[10px] font-mono text-neutral-600 mb-3">Adiciona todos os contatos com as etiquetas selecionadas.</p>
              <div
                v-for="label in labelsStore.labels"
                :key="label.id"
                @click="toggleLabel(label.id)"
                class="flex items-center gap-3 px-3 py-2.5 border cursor-pointer transition-colors"
                :class="selectedLabelIds.includes(label.id) ? 'border-accent/30 bg-accent/5' : 'border-white/5 hover:border-white/10'"
              >
                <div class="w-2 h-2 rounded-full shrink-0" :style="`background: ${label.color}`" />
                <span class="flex-1 text-xs text-white">{{ label.name }}</span>
                <Icon
                  v-if="selectedLabelIds.includes(label.id)"
                  icon="solar:check-circle-bold-duotone"
                  class="text-sm text-accent shrink-0"
                />
              </div>
              <p v-if="!labelsStore.labels.length" class="text-[10px] font-mono text-neutral-700 py-4 text-center">
                Nenhuma etiqueta criada
              </p>
            </template>

            <!-- Manual -->
            <template v-else-if="addTab === 'manual'">
              <input
                v-model="contactSearch"
                type="text"
                placeholder="Buscar contato..."
                class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20 placeholder:text-neutral-600 mb-2"
              />
              <div
                v-for="contact in filteredContacts.slice(0, 50)"
                :key="contact.id"
                @click="toggleContact(contact.id)"
                class="flex items-center gap-3 px-3 py-2.5 border cursor-pointer transition-colors"
                :class="selectedContactIds.includes(contact.id) ? 'border-accent/30 bg-accent/5' : 'border-white/5 hover:border-white/10'"
              >
                <div class="flex-1 min-w-0">
                  <p class="text-xs text-white truncate">{{ contact.name }}</p>
                  <p class="text-[10px] font-mono text-neutral-600">{{ contact.phone }}</p>
                </div>
                <Icon
                  v-if="selectedContactIds.includes(contact.id)"
                  icon="solar:check-circle-bold-duotone"
                  class="text-sm text-accent shrink-0"
                />
              </div>
              <p v-if="!filteredContacts.length" class="text-[10px] font-mono text-neutral-700 py-4 text-center">
                Nenhum contato encontrado
              </p>
            </template>

            <!-- Todos -->
            <template v-else>
              <div class="py-6 text-center space-y-3">
                <Icon icon="solar:users-group-rounded-bold-duotone" class="text-3xl text-white/20 mx-auto" />
                <p class="text-xs font-mono text-white">Adicionar todos os contatos</p>
                <p class="text-[10px] font-mono text-neutral-600">
                  Todos os contatos da organização serão adicionados à campanha.
                </p>
              </div>
            </template>

          </div>

          <!-- Footer -->
          <div class="px-5 py-4 border-t border-white/5 shrink-0">
            <p v-if="addError" class="text-[10px] font-mono text-red-400 mb-2">{{ addError }}</p>
            <div class="flex justify-end gap-2">
              <button
                @click="addModal = false"
                class="px-3 py-2 text-xs font-mono text-neutral-400 hover:text-white border border-white/10 hover:border-white/20 transition-colors"
              >Cancelar</button>
              <button
                @click="doAddContacts"
                :disabled="addingContacts"
                class="px-4 py-2 text-xs font-mono bg-accent text-black uppercase tracking-wider disabled:opacity-50 hover:opacity-90 transition-opacity flex items-center gap-2"
              >
                <div v-if="addingContacts" class="w-3 h-3 border border-black/30 border-t-black rounded-full animate-spin" />
                Adicionar
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
