<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'

const props = defineProps<{
  open: boolean
  agent: any | null
  providers: any[]
}>()
const emit = defineEmits<{ close: []; saved: [agent: any, isEdit: boolean] }>()

const api = useApi()

// ---------------------------------------------------------------------------
// Modelos disponíveis por provedor
// ---------------------------------------------------------------------------
const MODELS: Record<string, string[]> = {
  openai: [
    'gpt-5.5', 'gpt-5.4', 'gpt-5.4-mini', 'gpt-5.4-nano',
    'gpt-5.2', 'gpt-5.1', 'gpt-5', 'gpt-5-mini', 'gpt-5-nano',
    'gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano',
    'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo',
    'o1', 'o1-mini', 'o3', 'o3-mini', 'o4-mini',
  ],
  anthropic: [
    'claude-opus-4-5', 'claude-sonnet-4-5',
    'claude-opus-4-6', 'claude-sonnet-4-6',
    'claude-haiku-4-5-20251001',
    'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022',
    'claude-3-opus-20240229',
  ],
  groq: [
    'llama-3.3-70b-versatile', 'llama-3.1-70b-versatile',
    'llama-3.1-8b-instant', 'llama3-70b-8192', 'llama3-8b-8192',
    'mixtral-8x7b-32768', 'gemma2-9b-it', 'gemma-7b-it',
  ],
}

const GROQ_TOOL_OK = new Set([
  'llama-3.3-70b-versatile',
  'llama-3.1-70b-versatile',
])

function modelLabel(provider: string, model: string) {
  if (provider === 'groq' && !GROQ_TOOL_OK.has(model)) {
    return `${model}  *modelos erram em tools`
  }
  return model
}

// ---------------------------------------------------------------------------
// Ferramentas disponíveis
// ---------------------------------------------------------------------------
const AVAILABLE_TOOLS = [
  { id: 'duckduckgo', name: 'Busca na Web',      desc: 'Busca informações atualizadas na internet via DuckDuckGo', icon: 'solar:global-bold-duotone' },
  { id: 'calculator', name: 'Calculadora',        desc: 'Resolve cálculos e operações matemáticas',                icon: 'solar:calculator-bold-duotone' },
  { id: 'wikipedia',  name: 'Wikipedia',          desc: 'Busca informações enciclopédicas na Wikipedia',           icon: 'solar:book-2-bold-duotone' },
  { id: 'datetime',   name: 'Data e Hora',        desc: 'Informa a data e hora atual ao agente',                   icon: 'solar:clock-circle-bold-duotone' },
  { id: 'yfinance',   name: 'Dados Financeiros',  desc: 'Preços de ações e cotações via Yahoo Finance',            icon: 'solar:chart-2-bold-duotone' },
]

// ---------------------------------------------------------------------------
// Estado
// ---------------------------------------------------------------------------
type Tab = 'geral' | 'conhecimento' | 'ferramentas' | 'memoria' | 'followup' | 'objetivo' | 'envio'

const tab = ref<Tab>('geral')

const form = reactive({
  name: '',
  description: '',
  system_prompt: '',
  model_name: '',
  provider_id: null as number | null,
  is_active: true,
  enabled_tools: [] as string[],
  memory_enabled: false,
  memory_type: 'per_contact' as 'per_contact' | 'global',
  follow_up_enabled: false,
  follow_up_delay: 30,
  max_follow_ups: 3,
  follow_up_prompt: '',
  follow_up_respect_hours: false,
  goal_enabled: false,
  goal_description: '',
  goal_slots: [] as { key: string; label: string; required: boolean; pipedrive_field?: string }[],
  goal_action: '' as '' | 'deactivate_ai' | 'close_conversation' | 'assign_to_user' | 'trigger_automation',
  goal_assign_to_id: null as number | null,
  goal_automation_id: null as number | null,
  goal_final_message: '',
  split_messages_enabled: false,
  split_typing_speed_ms_per_char: 35,
  split_min_delay_ms: 600,
  split_max_delay_ms: 3500,
  accumulate_messages_enabled: false,
  accumulate_window_seconds: 10,
})

const members = ref<any[]>([])
const membersLoading = ref(false)
const fetchMembers = async () => {
  if (members.value.length || membersLoading.value) return
  membersLoading.value = true
  try {
    members.value = await api<any[]>('/api/org/members')
  } catch {}
  finally { membersLoading.value = false }
}

const pipedriveActive = ref(false)
const dealFields = ref<{ key: string; name: string }[]>([])
const goalAutomations = ref<any[]>([])
let objetivoExtrasLoaded = false
const fetchObjetivoExtras = async () => {
  if (objetivoExtrasLoaded) return
  objetivoExtrasLoaded = true
  try {
    const integ = await api<any>('/api/org/integrations/pipedrive')
    pipedriveActive.value = !!integ?.is_active
    if (pipedriveActive.value) {
      dealFields.value = await api<{ key: string; name: string }[]>('/api/org/integrations/pipedrive/deal-fields')
    }
  } catch {}
  try {
    const autos = await api<any[]>('/api/automations/')
    goalAutomations.value = autos.filter(a => a.trigger_type === 'agent.goal_completed')
  } catch {}
}

const loading = ref(false)
const error = ref('')

// Conhecimento
const documents = ref<any[]>([])
const docsLoading = ref(false)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)
let pollingTimer: ReturnType<typeof setInterval> | null = null

// Custom HTTP Tools
const customTools = ref<any[]>([])
const customToolsLoading = ref(false)
const showHttpToolForm = ref(false)
const editingToolId = ref<number | null>(null)
const httpToolForm = reactive({
  name: '',
  description: '',
  method: 'POST',
  url: '',
  body_template: '',
  headers: [] as { key: string; value: string }[],
})
const httpToolError = ref('')
const savingHttpTool = ref(false)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------
const isEdit = computed(() => !!props.agent)

const selectedProviderType = computed(
  () => props.providers.find((p: any) => p.id === form.provider_id)?.provider_type ?? '',
)

const availableModels = computed(() => MODELS[selectedProviderType.value] ?? [])

const tabsDisabled = computed(() => !isEdit.value)

// ---------------------------------------------------------------------------
// Watchers
// ---------------------------------------------------------------------------
watch(() => props.open, (val) => {
  if (!val) {
    stopPolling()
    return
  }
  error.value = ''
  tab.value = 'geral'
  documents.value = []
  customTools.value = []
  showHttpToolForm.value = false

  if (props.agent) {
    form.name         = props.agent.name
    form.description  = props.agent.description
    form.system_prompt = props.agent.system_prompt
    form.model_name   = props.agent.model_name
    form.provider_id  = props.agent.provider.id
    form.is_active    = props.agent.is_active
    form.enabled_tools      = props.agent.enabled_tools      ?? []
    form.memory_enabled     = props.agent.memory_enabled     ?? false
    form.memory_type        = props.agent.memory_type        ?? 'per_contact'
    form.follow_up_enabled       = props.agent.follow_up_enabled       ?? false
    form.follow_up_delay         = Math.max(30, props.agent.follow_up_delay ?? 30)
    form.max_follow_ups          = props.agent.max_follow_ups          ?? 3
    form.follow_up_prompt        = props.agent.follow_up_prompt        ?? ''
    form.follow_up_respect_hours = props.agent.follow_up_respect_hours ?? false
    form.goal_enabled         = props.agent.goal_enabled         ?? false
    form.goal_description     = props.agent.goal_description     ?? ''
    form.goal_slots           = props.agent.goal_slots           ?? []
    form.goal_action          = props.agent.goal_action          ?? ''
    form.goal_assign_to_id    = props.agent.goal_assign_to_id    ?? null
    form.goal_automation_id   = props.agent.goal_automation_id   ?? null
    form.goal_final_message   = props.agent.goal_final_message   ?? ''
    form.split_messages_enabled         = props.agent.split_messages_enabled         ?? false
    form.split_typing_speed_ms_per_char = props.agent.split_typing_speed_ms_per_char ?? 35
    form.split_min_delay_ms             = props.agent.split_min_delay_ms             ?? 600
    form.split_max_delay_ms             = props.agent.split_max_delay_ms             ?? 3500
    form.accumulate_messages_enabled    = props.agent.accumulate_messages_enabled    ?? false
    form.accumulate_window_seconds      = props.agent.accumulate_window_seconds      ?? 10
  } else {
    form.name         = ''
    form.description  = ''
    form.system_prompt = ''
    form.provider_id  = props.providers[0]?.id ?? null
    form.model_name   = ''
    form.is_active    = true
    form.enabled_tools     = []
    form.memory_enabled    = false
    form.memory_type       = 'per_contact'
    form.follow_up_enabled       = false
    form.follow_up_delay         = 60
    form.max_follow_ups          = 3
    form.follow_up_prompt        = ''
    form.follow_up_respect_hours = false
    form.goal_enabled         = false
    form.goal_description     = ''
    form.goal_slots           = []
    form.goal_action          = ''
    form.goal_assign_to_id    = null
    form.goal_automation_id   = null
    form.goal_final_message   = ''
    form.split_messages_enabled         = false
    form.split_typing_speed_ms_per_char = 35
    form.split_min_delay_ms             = 600
    form.split_max_delay_ms             = 3500
    form.accumulate_messages_enabled    = false
    form.accumulate_window_seconds      = 10
  }
})

watch(selectedProviderType, () => {
  if (!availableModels.value.includes(form.model_name)) {
    form.model_name = availableModels.value[0] ?? ''
  }
}, { immediate: false })

watch(tab, async (val) => {
  if (val === 'conhecimento' && isEdit.value) {
    await fetchDocuments()
  }
  if (val === 'ferramentas' && isEdit.value) {
    await fetchCustomTools()
  }
  if (val === 'objetivo') {
    await fetchMembers()
    await fetchObjetivoExtras()
  }
})

const addSlot = () => form.goal_slots.push({ key: '', label: '', required: false, pipedrive_field: '' })
const removeSlot = (idx: number) => form.goal_slots.splice(idx, 1)

// ---------------------------------------------------------------------------
// Submit principal
// ---------------------------------------------------------------------------
const submit = async () => {
  if (!form.name.trim() || !form.system_prompt.trim() || !form.provider_id || !form.model_name) return
  if (form.follow_up_enabled && form.follow_up_delay < 30) {
    error.value = 'O intervalo de follow-up não pode ser menor que 30 minutos.'
    return
  }
  if (form.goal_enabled) {
    if (!form.goal_description.trim()) {
      error.value = 'Descreva o objetivo ou desabilite a aba Objetivo.'
      return
    }
    if (!form.goal_action) {
      error.value = 'Selecione uma ação ao concluir o objetivo.'
      return
    }
    if (form.goal_action === 'assign_to_user' && !form.goal_assign_to_id) {
      error.value = 'Selecione o operador para atribuição.'
      return
    }
    if (form.goal_action === 'trigger_automation' && !form.goal_automation_id) {
      error.value = 'Selecione a automação a disparar.'
      return
    }
  }
  if (form.split_messages_enabled && form.split_min_delay_ms > form.split_max_delay_ms) {
    error.value = 'Delay mínimo deve ser menor ou igual ao delay máximo.'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const body = { ...form }
    let agent: any
    if (isEdit.value) {
      agent = await api<any>(`/api/agents/${props.agent.id}`, { method: 'PUT', body })
    } else {
      agent = await api<any>('/api/agents/', { method: 'POST', body })
    }
    emit('saved', agent, isEdit.value)
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao salvar agente'
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// Ferramentas — toggle
// ---------------------------------------------------------------------------
const toggleTool = (id: string) => {
  const idx = form.enabled_tools.indexOf(id)
  if (idx === -1) form.enabled_tools.push(id)
  else form.enabled_tools.splice(idx, 1)
}

// ---------------------------------------------------------------------------
// Conhecimento — documentos
// ---------------------------------------------------------------------------
const fetchDocuments = async () => {
  if (!props.agent?.id) return
  docsLoading.value = true
  try {
    documents.value = await api<any[]>(`/api/agents/${props.agent.id}/documents`)
  } catch {}
  finally { docsLoading.value = false }
}

const startPollingPending = () => {
  stopPolling()
  pollingTimer = setInterval(async () => {
    const hasPending = documents.value.some(d => d.status === 'pending' || d.status === 'processing')
    if (!hasPending) { stopPolling(); return }
    await fetchDocuments()
  }, 3000)
}

const stopPolling = () => {
  if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null }
}

const handleFileSelect = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) uploadFile(input.files[0])
  input.value = ''
}

const handleDrop = (e: DragEvent) => {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}

const uploadFile = async (file: File) => {
  if (!props.agent?.id) return
  const ext = file.name.split('.').pop()?.toLowerCase()
  const allowed = ['pdf', 'txt', 'md']
  if (!allowed.includes(ext ?? '')) {
    error.value = 'Formato não suportado. Use PDF, TXT ou MD.'
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    error.value = 'Arquivo muito grande. Máximo 10 MB.'
    return
  }
  uploading.value = true
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    const doc = await api<any>(`/api/agents/${props.agent.id}/documents`, {
      method: 'POST',
      body: formData,
    })
    documents.value.unshift(doc)
    startPollingPending()
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao enviar arquivo'
  } finally {
    uploading.value = false
  }
}

const deleteDocument = async (docId: number) => {
  if (!props.agent?.id) return
  try {
    await api(`/api/agents/${props.agent.id}/documents/${docId}`, { method: 'DELETE' })
    documents.value = documents.value.filter(d => d.id !== docId)
  } catch {}
}

const docStatusClass = (status: string) => {
  if (status === 'ready')    return 'text-green-400 bg-green-400/10'
  if (status === 'failed')   return 'text-red-400 bg-red-400/10'
  return 'text-yellow-400 bg-yellow-400/10'
}
const docStatusLabel = (status: string) => {
  if (status === 'ready')    return 'Pronto'
  if (status === 'failed')   return 'Falhou'
  return 'Processando…'
}

const docExt = (name: string) => name.split('.').pop()?.toLowerCase() ?? ''

// ---------------------------------------------------------------------------
// Custom HTTP Tools
// ---------------------------------------------------------------------------
const fetchCustomTools = async () => {
  if (!props.agent?.id) return
  customToolsLoading.value = true
  try {
    customTools.value = await api<any[]>(`/api/agents/${props.agent.id}/tools`)
  } catch {}
  finally { customToolsLoading.value = false }
}

const openHttpToolForm = (tool?: any) => {
  httpToolError.value = ''
  if (tool) {
    editingToolId.value = tool.id
    httpToolForm.name = tool.name
    httpToolForm.description = tool.description
    httpToolForm.method = tool.method
    httpToolForm.url = tool.url
    httpToolForm.body_template = tool.body_template
    httpToolForm.headers = Object.entries(tool.headers || {}).map(([k, v]) => ({ key: k, value: v as string }))
  } else {
    editingToolId.value = null
    httpToolForm.name = ''
    httpToolForm.description = ''
    httpToolForm.method = 'POST'
    httpToolForm.url = ''
    httpToolForm.body_template = ''
    httpToolForm.headers = []
  }
  showHttpToolForm.value = true
}

const closeHttpToolForm = () => {
  showHttpToolForm.value = false
  editingToolId.value = null
}

const saveHttpTool = async () => {
  if (!props.agent?.id) return
  if (!httpToolForm.name.trim() || !httpToolForm.url.trim() || !httpToolForm.description.trim()) {
    httpToolError.value = 'Nome, URL e descrição são obrigatórios'
    return
  }
  savingHttpTool.value = true
  httpToolError.value = ''
  try {
    const headers = Object.fromEntries(
      httpToolForm.headers.filter(h => h.key.trim()).map(h => [h.key.trim(), h.value])
    )
    const body = {
      name: httpToolForm.name,
      description: httpToolForm.description,
      method: httpToolForm.method,
      url: httpToolForm.url,
      body_template: httpToolForm.body_template,
      headers,
    }
    if (editingToolId.value) {
      const updated = await api<any>(`/api/agents/${props.agent.id}/tools/${editingToolId.value}`, { method: 'PUT', body })
      const idx = customTools.value.findIndex(t => t.id === editingToolId.value)
      if (idx !== -1) customTools.value[idx] = updated
    } else {
      const created = await api<any>(`/api/agents/${props.agent.id}/tools`, { method: 'POST', body })
      customTools.value.unshift(created)
    }
    closeHttpToolForm()
  } catch (e: any) {
    httpToolError.value = e?.data?.detail || 'Erro ao salvar tool'
  } finally {
    savingHttpTool.value = false
  }
}

const deleteCustomTool = async (toolId: number) => {
  if (!props.agent?.id) return
  try {
    await api(`/api/agents/${props.agent.id}/tools/${toolId}`, { method: 'DELETE' })
    customTools.value = customTools.value.filter(t => t.id !== toolId)
  } catch {}
}

const addHeader = () => httpToolForm.headers.push({ key: '', value: '' })
const removeHeader = (idx: number) => httpToolForm.headers.splice(idx, 1)
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="emit('close')"></div>

        <div class="relative bg-surface border border-white/10 w-full max-w-2xl z-10 flex flex-col max-h-[90vh]">
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <!-- Header -->
          <div class="px-6 pt-6 pb-4 shrink-0">
            <p class="field-label mb-0.5">Agente de IA</p>
            <h2 class="text-lg font-medium text-white tracking-tight">
              {{ isEdit ? 'Editar agente' : 'Novo agente' }}
            </h2>
          </div>

          <!-- Aviso de sem provedor -->
          <div v-if="providers.length === 0" class="px-6 mb-3 shrink-0">
            <div class="bg-yellow-500/5 border border-yellow-500/20 p-3">
              <p class="text-xs font-mono text-yellow-500">Configure ao menos um provedor antes de criar um agente.</p>
            </div>
          </div>

          <!-- Tabs -->
          <div class="flex border-b border-white/5 px-6 shrink-0">
            <button
              v-for="[key, label] in [['geral','Geral'],['conhecimento','Conhecimento'],['ferramentas','Ferramentas'],['memoria','Memória'],['followup','Follow-up'],['objetivo','Objetivo'],['envio','Envio']]"
              :key="key"
              @click="key === 'geral' || !tabsDisabled ? tab = key as Tab : null"
              class="pb-2.5 mr-5 text-[10px] font-mono uppercase tracking-widest transition-colors border-b-2 -mb-px"
              :class="[
                tab === key ? 'text-accent border-accent' : 'border-transparent',
                key !== 'geral' && tabsDisabled
                  ? 'text-neutral-800 cursor-not-allowed'
                  : tab !== key ? 'text-neutral-600 hover:text-neutral-400' : '',
              ]"
              :title="key !== 'geral' && tabsDisabled ? 'Crie e salve o agente primeiro' : undefined"
            >
              {{ label }}
            </button>
          </div>

          <!-- Conteúdo scrollável -->
          <div class="flex-1 overflow-y-auto px-6 py-5">

            <!-- ===================== ABA GERAL ===================== -->
            <div v-if="tab === 'geral'" class="space-y-3">
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="field-label">Nome</label>
                  <div class="input-wrapper">
                    <input v-model="form.name" type="text" placeholder="Atendente Virtual" required class="input-field" />
                  </div>
                </div>
                <div>
                  <label class="field-label">Descrição <span class="text-neutral-700 normal-case">(opcional)</span></label>
                  <div class="input-wrapper">
                    <input v-model="form.description" type="text" placeholder="Suporte ao cliente" class="input-field" />
                  </div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="field-label">Provedor</label>
                  <div class="bg-surface border border-white/10 rounded-full py-2.5 pl-5 pr-3 hover:border-accent/50 transition-colors">
                    <select v-model="form.provider_id" class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer">
                      <option v-for="p in providers" :key="p.id" :value="p.id" class="bg-surface text-white">
                        {{ p.provider_type.charAt(0).toUpperCase() + p.provider_type.slice(1) }}
                      </option>
                    </select>
                  </div>
                </div>
                <div>
                  <label class="field-label">Modelo</label>
                  <div class="bg-surface border border-white/10 rounded-full py-2.5 pl-5 pr-3 hover:border-accent/50 transition-colors">
                    <select v-model="form.model_name" class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer">
                      <option v-for="m in availableModels" :key="m" :value="m" class="bg-surface text-white">{{ modelLabel(selectedProviderType, m) }}</option>
                    </select>
                  </div>
                </div>
              </div>

              <div>
                <label class="field-label">System Prompt</label>
                <MdEditor
                  v-model="form.system_prompt"
                  language="en-US"
                  theme="dark"
                  :toolbars="['bold','italic','strikethrough','|','title','quote','code','codeRow','|','unorderedList','orderedList','|','fullscreen']"
                  :preview="false"
                  :style="{ height: '180px', borderColor: 'rgba(255,255,255,0.1)', fontSize: '13px' }"
                  placeholder="Você é um assistente de atendimento ao cliente. Responda sempre em português, de forma educada e objetiva..."
                />
              </div>

              <div class="flex items-center justify-between py-2.5 border-t border-white/5">
                <div>
                  <p class="text-sm text-white">Agente ativo</p>
                  <p class="text-[10px] font-mono text-neutral-600">Inativos não respondem mensagens</p>
                </div>
                <button
                  type="button"
                  @click="form.is_active = !form.is_active"
                  class="relative w-10 h-5 rounded-full transition-colors flex-shrink-0"
                  :class="form.is_active ? 'bg-accent' : 'bg-neutral-800'"
                >
                  <span
                    class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                    :class="form.is_active ? 'translate-x-5' : 'translate-x-0'"
                  ></span>
                </button>
              </div>
            </div>

            <!-- ===================== ABA CONHECIMENTO ===================== -->
            <div v-else-if="tab === 'conhecimento'" class="space-y-4">
              <!-- Área de upload -->
              <div
                class="border-2 border-dashed border-white/10 p-8 text-center transition-colors cursor-pointer hover:border-accent/40"
                :class="dragOver ? 'border-accent/60 bg-accent/5' : ''"
                @dragover.prevent="dragOver = true"
                @dragleave="dragOver = false"
                @drop.prevent="handleDrop"
                @click="fileInputRef?.click()"
              >
                <input
                  ref="fileInputRef"
                  type="file"
                  accept=".pdf,.txt,.md"
                  class="hidden"
                  @change="handleFileSelect"
                />
                <Icon icon="solar:upload-bold-duotone" class="text-3xl text-neutral-600 mb-2 mx-auto" />
                <p class="text-sm text-neutral-400 font-mono">
                  {{ uploading ? 'Enviando…' : 'Arraste ou clique para enviar' }}
                </p>
                <p class="text-[10px] font-mono text-neutral-700 mt-1">PDF, TXT, MD · máx. 10 MB</p>
              </div>

              <!-- Lista de documentos -->
              <div v-if="docsLoading" class="space-y-2">
                <div v-for="i in 3" :key="i" class="h-10 bg-white/5 animate-pulse rounded"></div>
              </div>

              <div v-else-if="documents.length === 0" class="flex flex-col items-center justify-center py-8 text-center">
                <Icon icon="solar:folder-open-bold-duotone" class="text-3xl text-white/10 mb-2" />
                <p class="text-xs font-mono text-neutral-700">Nenhum documento adicionado</p>
              </div>

              <div v-else class="space-y-1.5">
                <div
                  v-for="doc in documents"
                  :key="doc.id"
                  class="flex items-center gap-3 px-4 py-3 bg-canvas border border-white/5"
                >
                  <Icon
                    :icon="docExt(doc.name) === 'pdf' ? 'solar:file-text-bold-duotone' : 'solar:document-bold-duotone'"
                    class="text-base text-neutral-500 shrink-0"
                  />
                  <span class="text-sm text-white truncate flex-1 font-mono">{{ doc.name }}</span>
                  <span
                    class="text-[9px] font-mono uppercase tracking-widest px-2 py-0.5 shrink-0"
                    :class="docStatusClass(doc.status)"
                  >
                    {{ docStatusLabel(doc.status) }}
                  </span>
                  <button
                    @click="deleteDocument(doc.id)"
                    class="text-neutral-600 hover:text-red-400 transition-colors shrink-0"
                    title="Remover"
                  >
                    <Icon icon="solar:trash-bin-minimalistic-bold-duotone" class="text-base" />
                  </button>
                </div>
              </div>
            </div>

            <!-- ===================== ABA FERRAMENTAS ===================== -->
            <div v-else-if="tab === 'ferramentas'" class="space-y-5">

              <!-- Ferramentas padrão -->
              <div class="space-y-2">
                <p class="text-[10px] font-mono text-neutral-600">
                  Ferramentas padrão permitem ao agente buscar informações externas em tempo real.
                </p>
                <div
                  v-for="tool in AVAILABLE_TOOLS"
                  :key="tool.id"
                  class="flex items-center gap-4 px-4 py-3.5 bg-canvas border border-white/5 hover:border-white/10 transition-colors"
                >
                  <Icon :icon="tool.icon" class="text-xl text-neutral-500 shrink-0" />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm text-white font-medium">{{ tool.name }}</p>
                    <p class="text-[11px] font-mono text-neutral-600 mt-0.5">{{ tool.desc }}</p>
                  </div>
                  <button
                    type="button"
                    @click="toggleTool(tool.id)"
                    class="relative w-10 h-5 rounded-full transition-colors flex-shrink-0"
                    :class="form.enabled_tools.includes(tool.id) ? 'bg-accent' : 'bg-neutral-800'"
                  >
                    <span
                      class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                      :class="form.enabled_tools.includes(tool.id) ? 'translate-x-5' : 'translate-x-0'"
                    ></span>
                  </button>
                </div>
              </div>

              <!-- Ferramentas HTTP -->
              <div class="border-t border-white/5 pt-4 space-y-3">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-xs font-mono text-neutral-400 uppercase tracking-widest">Ferramentas HTTP</p>
                    <p class="text-[10px] font-mono text-neutral-700 mt-0.5">
                      Use <span class="text-neutral-500">{variavel}</span> na URL e no body para que a IA preencha os valores.
                    </p>
                  </div>
                  <button
                    v-if="!showHttpToolForm"
                    type="button"
                    @click="openHttpToolForm()"
                    class="flex items-center gap-1.5 px-3 py-1.5 border border-white/10 text-neutral-400 text-[10px] font-mono uppercase tracking-wider hover:border-accent/50 hover:text-accent transition-colors"
                  >
                    <Icon icon="solar:add-circle-bold-duotone" class="text-sm" />
                    Nova tool
                  </button>
                </div>

                <!-- Formulário criar/editar -->
                <Transition name="fade">
                  <div v-if="showHttpToolForm" class="bg-canvas border border-white/10 p-4 space-y-3">
                    <div class="grid grid-cols-2 gap-3">
                      <div>
                        <label class="field-label">Nome <span class="text-neutral-700 normal-case">(slug)</span></label>
                        <div class="input-wrapper">
                          <input v-model="httpToolForm.name" type="text" placeholder="consultar_estoque" class="input-field font-mono" />
                        </div>
                      </div>
                      <div>
                        <label class="field-label">Método</label>
                        <div class="bg-surface border border-white/10 py-2.5 pl-5 pr-3 hover:border-accent/50 transition-colors">
                          <select v-model="httpToolForm.method" class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer">
                            <option v-for="m in ['GET','POST','PUT','PATCH','DELETE']" :key="m" :value="m" class="bg-surface">{{ m }}</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    <div>
                      <label class="field-label">Descrição <span class="text-neutral-700 normal-case">(instrução para a IA)</span></label>
                      <div class="input-wrapper">
                        <input v-model="httpToolForm.description" type="text" placeholder="Consulta o estoque de um produto pelo SKU" class="input-field" />
                      </div>
                    </div>

                    <div>
                      <label class="field-label">URL</label>
                      <div class="input-wrapper">
                        <input v-model="httpToolForm.url" type="text" placeholder="https://api.exemplo.com/produtos/{sku}" class="input-field font-mono text-xs" />
                      </div>
                    </div>

                    <!-- Headers -->
                    <div class="space-y-2">
                      <div class="flex items-center justify-between">
                        <label class="field-label mb-0">Headers</label>
                        <button type="button" @click="addHeader" class="text-[10px] font-mono text-neutral-600 hover:text-accent transition-colors flex items-center gap-1">
                          <Icon icon="solar:add-circle-bold-duotone" class="text-xs" /> Adicionar
                        </button>
                      </div>
                      <div v-if="httpToolForm.headers.length === 0" class="text-[10px] font-mono text-neutral-700">
                        Nenhum header configurado
                      </div>
                      <div v-for="(h, idx) in httpToolForm.headers" :key="idx" class="flex gap-2">
                        <div class="input-wrapper flex-1 !rounded-none !py-2 !px-3">
                          <input v-model="h.key" type="text" placeholder="Authorization" class="input-field text-xs" />
                        </div>
                        <div class="input-wrapper flex-1 !rounded-none !py-2 !px-3">
                          <input v-model="h.value" type="text" placeholder="Bearer {token}" class="input-field text-xs" />
                        </div>
                        <button type="button" @click="removeHeader(idx)" class="text-neutral-600 hover:text-red-400 transition-colors px-1">
                          <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
                        </button>
                      </div>
                    </div>

                    <div>
                      <label class="field-label">Body <span class="text-neutral-700 normal-case">(JSON — opcional)</span></label>
                      <div class="input-wrapper !rounded-none !py-2 !px-3">
                        <textarea
                          v-model="httpToolForm.body_template"
                          rows="3"
                          placeholder='{"sku": "{sku}", "quantidade": "{qtd}"}'
                          class="input-field text-xs resize-none"
                        />
                      </div>
                    </div>

                    <p v-if="httpToolError" class="text-xs font-mono text-red-400">{{ httpToolError }}</p>

                    <div class="flex gap-2 pt-1">
                      <button type="button" @click="closeHttpToolForm" class="flex-1 py-2 border border-white/10 text-neutral-400 text-[10px] font-mono uppercase tracking-wider hover:border-white/20 transition-colors">
                        Cancelar
                      </button>
                      <button type="button" @click="saveHttpTool" :disabled="savingHttpTool" class="flex-1 py-2 bg-accent/10 border border-accent/30 text-accent text-[10px] font-mono uppercase tracking-wider hover:bg-accent/20 transition-colors disabled:opacity-50">
                        {{ savingHttpTool ? 'Salvando…' : editingToolId ? 'Atualizar' : 'Criar tool' }}
                      </button>
                    </div>
                  </div>
                </Transition>

                <!-- Lista de custom tools -->
                <div v-if="customToolsLoading" class="space-y-2">
                  <div v-for="i in 2" :key="i" class="h-12 bg-white/5 animate-pulse"></div>
                </div>

                <div v-else-if="customTools.length === 0 && !showHttpToolForm" class="flex flex-col items-center justify-center py-6 text-center">
                  <Icon icon="solar:plug-circle-bold-duotone" class="text-2xl text-white/10 mb-2" />
                  <p class="text-xs font-mono text-neutral-700">Nenhuma tool HTTP configurada</p>
                </div>

                <div v-else class="space-y-1.5">
                  <div
                    v-for="tool in customTools"
                    :key="tool.id"
                    class="flex items-center gap-3 px-4 py-3 bg-canvas border border-white/5"
                  >
                    <Icon icon="solar:routing-bold-duotone" class="text-base text-neutral-500 shrink-0" />
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2">
                        <span class="text-xs font-mono text-white">{{ tool.name }}</span>
                        <span class="text-[9px] font-mono text-neutral-600 bg-white/5 px-1.5 py-0.5">{{ tool.method }}</span>
                      </div>
                      <p class="text-[10px] font-mono text-neutral-600 truncate mt-0.5">{{ tool.url }}</p>
                    </div>
                    <button @click="openHttpToolForm(tool)" class="text-neutral-600 hover:text-accent transition-colors shrink-0" title="Editar">
                      <Icon icon="solar:pen-bold-duotone" class="text-base" />
                    </button>
                    <button @click="deleteCustomTool(tool.id)" class="text-neutral-600 hover:text-red-400 transition-colors shrink-0" title="Remover">
                      <Icon icon="solar:trash-bin-minimalistic-bold-duotone" class="text-base" />
                    </button>
                  </div>
                </div>
              </div>

            </div>

            <!-- ===================== ABA MEMÓRIA ===================== -->
            <div v-else-if="tab === 'memoria'" class="space-y-4">
              <!-- Toggle habilitar -->
              <div class="flex items-center justify-between py-3 border-b border-white/5">
                <div>
                  <p class="text-sm text-white">Habilitar memória</p>
                  <p class="text-[10px] font-mono text-neutral-600 mt-0.5">
                    O agente lembra de informações de conversas anteriores
                  </p>
                </div>
                <button
                  type="button"
                  @click="form.memory_enabled = !form.memory_enabled"
                  class="relative w-10 h-5 rounded-full transition-colors flex-shrink-0"
                  :class="form.memory_enabled ? 'bg-accent' : 'bg-neutral-800'"
                >
                  <span
                    class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                    :class="form.memory_enabled ? 'translate-x-5' : 'translate-x-0'"
                  ></span>
                </button>
              </div>

              <!-- Tipo de memória -->
              <Transition name="fade">
                <div v-if="form.memory_enabled" class="space-y-2">
                  <label class="field-label">Tipo de memória</label>
                  <div class="space-y-2">
                    <label
                      class="flex items-start gap-3 px-4 py-3.5 bg-canvas border cursor-pointer transition-colors"
                      :class="form.memory_type === 'per_contact' ? 'border-accent/40 bg-accent/5' : 'border-white/5 hover:border-white/10'"
                    >
                      <input
                        type="radio"
                        v-model="form.memory_type"
                        value="per_contact"
                        class="mt-0.5 accent-[rgb(var(--accent-rgb))] shrink-0"
                      />
                      <div>
                        <p class="text-sm text-white font-medium">Por contato</p>
                        <p class="text-[11px] font-mono text-neutral-600 mt-0.5">
                          O agente lembra de informações individuais de cada contato entre conversas
                        </p>
                      </div>
                    </label>
                    <label
                      class="flex items-start gap-3 px-4 py-3.5 bg-canvas border cursor-pointer transition-colors"
                      :class="form.memory_type === 'global' ? 'border-accent/40 bg-accent/5' : 'border-white/5 hover:border-white/10'"
                    >
                      <input
                        type="radio"
                        v-model="form.memory_type"
                        value="global"
                        class="mt-0.5 accent-[rgb(var(--accent-rgb))] shrink-0"
                      />
                      <div>
                        <p class="text-sm text-white font-medium">Global</p>
                        <p class="text-[11px] font-mono text-neutral-600 mt-0.5">
                          O agente mantém um contexto compartilhado entre todos os contatos
                        </p>
                      </div>
                    </label>
                  </div>
                </div>
              </Transition>

              <div v-if="!form.memory_enabled" class="flex flex-col items-center justify-center py-8 text-center">
                <Icon icon="solar:brain-bold-duotone" class="text-3xl text-white/10 mb-2" />
                <p class="text-xs font-mono text-neutral-700">Memória desabilitada</p>
              </div>
            </div>

            <!-- ===================== ABA FOLLOW-UP ===================== -->
            <div v-else-if="tab === 'followup'" class="space-y-4">

              <!-- Toggle habilitar -->
              <div class="flex items-center justify-between py-3 border-b border-white/5">
                <div>
                  <p class="text-sm text-white">Follow-up automático</p>
                  <p class="text-[10px] font-mono text-neutral-600 mt-0.5">
                    A IA envia mensagens quando o contato não responde
                  </p>
                </div>
                <button
                  type="button"
                  @click="form.follow_up_enabled = !form.follow_up_enabled"
                  class="relative w-10 h-5 rounded-full transition-colors flex-shrink-0"
                  :class="form.follow_up_enabled ? 'bg-accent' : 'bg-neutral-800'"
                >
                  <span
                    class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                    :class="form.follow_up_enabled ? 'translate-x-5' : 'translate-x-0'"
                  ></span>
                </button>
              </div>

              <!-- Configurações condicionais -->
              <Transition name="fade">
                <div v-if="form.follow_up_enabled" class="space-y-4">

                  <!-- Delay + max -->
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="field-label">Delay <span class="text-neutral-700 normal-case">(minutos)</span></label>
                      <div class="input-wrapper">
                        <input
                          v-model.number="form.follow_up_delay"
                          type="number" min="30" max="10080"
                          class="input-field"
                        />
                      </div>
                      <p class="text-[10px] font-mono text-neutral-700 mt-1">Tempo sem resposta antes de reenviar</p>
                    </div>
                    <div>
                      <label class="field-label">Máximo de tentativas</label>
                      <div class="input-wrapper">
                        <input
                          v-model.number="form.max_follow_ups"
                          type="number" min="1" max="10"
                          class="input-field"
                        />
                      </div>
                      <p class="text-[10px] font-mono text-neutral-700 mt-1">Após atingir, para silenciosamente</p>
                    </div>
                  </div>

                  <!-- Instrução de follow-up -->
                  <div>
                    <label class="field-label">Instrução para a IA <span class="text-neutral-700 normal-case">(opcional)</span></label>
                    <div class="input-wrapper !py-0 !px-0">
                      <textarea
                        v-model="form.follow_up_prompt"
                        rows="4"
                        placeholder="O usuário não respondeu. Envie uma mensagem amigável para retomar a conversa, mencionando o assunto anterior e oferecendo ajuda."
                        class="input-field resize-none !py-2.5 !px-3"
                      />
                    </div>
                    <p class="text-[10px] font-mono text-neutral-700 mt-1">
                      Instrução extra injetada no system prompt ao gerar o follow-up. O histórico completo da conversa é sempre incluído.
                    </p>
                  </div>

                  <!-- Horários de atendimento -->
                  <div class="flex items-center justify-between py-3 border-t border-white/5">
                    <div>
                      <p class="text-sm text-white">Respeitar horários de atendimento</p>
                      <p class="text-[10px] font-mono text-neutral-600 mt-0.5">
                        Follow-ups só são enviados dentro do horário configurado na organização
                      </p>
                    </div>
                    <button
                      type="button"
                      @click="form.follow_up_respect_hours = !form.follow_up_respect_hours"
                      class="relative w-10 h-5 rounded-full transition-colors flex-shrink-0"
                      :class="form.follow_up_respect_hours ? 'bg-accent' : 'bg-neutral-800'"
                    >
                      <span
                        class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                        :class="form.follow_up_respect_hours ? 'translate-x-5' : 'translate-x-0'"
                      ></span>
                    </button>
                  </div>

                  <!-- Resumo -->
                  <div class="bg-accent/5 border border-accent/20 px-4 py-3">
                    <p class="text-[11px] font-mono text-accent/80 leading-relaxed">
                      A IA enviará até <strong class="text-accent">{{ form.max_follow_ups }}</strong> follow-up{{ form.max_follow_ups !== 1 ? 's' : '' }}
                      com intervalo de <strong class="text-accent">{{ form.follow_up_delay }} min</strong> entre cada.
                      O ciclo reinicia quando o contato responder.
                      <template v-if="form.follow_up_respect_hours"> Respeita horários de atendimento da organização.</template>
                    </p>
                  </div>
                </div>
              </Transition>

              <div v-if="!form.follow_up_enabled" class="flex flex-col items-center justify-center py-8 text-center">
                <Icon icon="solar:bell-off-bold-duotone" class="text-3xl text-white/10 mb-2" />
                <p class="text-xs font-mono text-neutral-700">Follow-up desabilitado</p>
              </div>
            </div>

            <!-- ===================== ABA OBJETIVO ===================== -->
            <div v-else-if="tab === 'objetivo'" class="space-y-4">

              <!-- Explicação inicial -->
              <div class="bg-blue-500/5 border border-blue-500/20 px-4 py-3">
                <div class="flex items-start gap-2">
                  <Icon icon="solar:info-circle-bold-duotone" class="text-base text-blue-400 shrink-0 mt-0.5" />
                  <div class="space-y-1.5">
                    <p class="text-[11px] font-mono text-blue-200/80 leading-relaxed">
                      <strong class="text-blue-300">O que é um objetivo?</strong>
                      Uma "meta" que a IA precisa cumprir na conversa. Quando a IA julgar que cumpriu,
                      ela encerra o atendimento automaticamente (segundo a ação escolhida).
                    </p>
                    <p class="text-[11px] font-mono text-blue-200/60 leading-relaxed">
                      <strong class="text-blue-300">Exemplo:</strong>
                      objetivo = "coletar nome + email + problema do cliente" → IA conversa naturalmente,
                      coleta os dados → ao ter tudo, marca como concluído → transfere para humano.
                    </p>
                  </div>
                </div>
              </div>

              <div class="flex items-center justify-between py-3 border-b border-white/5">
                <div>
                  <p class="text-sm text-white">Ativar objetivo para este agente</p>
                  <p class="text-[10px] font-mono text-neutral-600 mt-0.5">
                    Desligado = IA conversa indefinidamente até alguém intervir manualmente
                  </p>
                </div>
                <button
                  type="button"
                  @click="form.goal_enabled = !form.goal_enabled"
                  class="relative w-10 h-5 rounded-full transition-colors flex-shrink-0"
                  :class="form.goal_enabled ? 'bg-accent' : 'bg-neutral-800'"
                >
                  <span
                    class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                    :class="form.goal_enabled ? 'translate-x-5' : 'translate-x-0'"
                  ></span>
                </button>
              </div>

              <Transition name="fade">
                <div v-if="form.goal_enabled" class="space-y-5">

                  <!-- PASSO 1: Descrição -->
                  <div>
                    <div class="flex items-center gap-2 mb-1.5">
                      <span class="text-[10px] font-mono text-accent bg-accent/10 px-1.5 py-0.5">PASSO 1</span>
                      <label class="field-label mb-0">O que a IA precisa fazer?</label>
                    </div>
                    <div class="input-wrapper !rounded-none !py-0 !px-0">
                      <textarea
                        v-model="form.goal_description"
                        rows="6"
                        placeholder="Descreva em linguagem natural, como se fosse para um funcionário. Ex: Qualificar o lead perguntando o nome da empresa, o tamanho do time e o orçamento mensal. Quando tiver as três informações, considere o objetivo cumprido."
                        class="input-field resize-y !py-2.5 !px-3"
                      />
                    </div>
                    <p class="text-[10px] font-mono text-neutral-700 mt-1">
                      Seja específico: a IA usa esse texto como instrução. Quanto mais claro, melhor ela acerta.
                    </p>
                  </div>

                  <!-- PASSO 2: Slots -->
                  <div class="space-y-2 border-t border-white/5 pt-4">
                    <div class="flex items-center gap-2 mb-1">
                      <span class="text-[10px] font-mono text-accent bg-accent/10 px-1.5 py-0.5">PASSO 2</span>
                      <label class="field-label mb-0">Quais dados a IA deve coletar? <span class="text-neutral-700 normal-case">(opcional, mas recomendado)</span></label>
                    </div>
                    <p class="text-[10px] font-mono text-neutral-600">
                      Cada linha é um campo a coletar. Dica: <strong class="text-neutral-400">chave técnica</strong> vira nome no CRM (sem espaços/acentos),
                      <strong class="text-neutral-400">rótulo</strong> é o nome humano. Ex: <code class="text-neutral-400">email</code> + "E-mail do cliente".
                    </p>
                    <div class="flex justify-end">
                      <button type="button" @click="addSlot" class="text-[10px] font-mono text-neutral-600 hover:text-accent transition-colors flex items-center gap-1">
                        <Icon icon="solar:add-circle-bold-duotone" class="text-xs" /> Adicionar campo
                      </button>
                    </div>
                    <div v-if="form.goal_slots.length === 0" class="text-[10px] font-mono text-neutral-700 px-3 py-3 border border-dashed border-white/10 text-center">
                      Nenhum campo definido — IA decide sozinha quando cumpriu o objetivo
                    </div>
                    <div v-else class="space-y-1.5">
                      <div
                        class="grid gap-2 text-[9px] font-mono text-neutral-600 uppercase tracking-widest px-1"
                        :class="pipedriveActive ? 'grid-cols-[1fr_1fr_1fr_auto_auto]' : 'grid-cols-[1fr_1fr_auto_auto]'"
                      >
                        <span>Chave técnica</span>
                        <span>Rótulo (humano)</span>
                        <span v-if="pipedriveActive">Campo no Pipedrive</span>
                        <span>Obrig.</span>
                        <span></span>
                      </div>
                      <div
                        v-for="(s, idx) in form.goal_slots"
                        :key="idx"
                        class="grid gap-2 items-center"
                        :class="pipedriveActive ? 'grid-cols-[1fr_1fr_1fr_auto_auto]' : 'grid-cols-[1fr_1fr_auto_auto]'"
                      >
                        <div class="input-wrapper !rounded-none !py-2 !px-3">
                          <input v-model="s.key" type="text" placeholder="ex: email" class="input-field font-mono text-xs" />
                        </div>
                        <div class="input-wrapper !rounded-none !py-2 !px-3">
                          <input v-model="s.label" type="text" placeholder="E-mail do cliente" class="input-field text-xs" />
                        </div>
                        <div v-if="pipedriveActive" class="input-wrapper !rounded-none !py-2 !px-3">
                          <select v-model="s.pipedrive_field" class="input-field text-xs bg-transparent appearance-none cursor-pointer">
                            <option value="" class="bg-surface">— não enviar —</option>
                            <option v-for="f in dealFields" :key="f.key" :value="f.key" class="bg-surface">{{ f.name }}</option>
                          </select>
                        </div>
                        <input type="checkbox" v-model="s.required" class="accent-[rgb(var(--accent-rgb))] w-4 h-4 justify-self-center" :title="s.required ? 'Obrigatório' : 'Opcional'" />
                        <button type="button" @click="removeSlot(idx)" class="text-neutral-600 hover:text-red-400 transition-colors px-1" title="Remover campo">
                          <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
                        </button>
                      </div>
                    </div>
                    <p v-if="pipedriveActive" class="text-[10px] font-mono text-neutral-600">
                      <Icon icon="solar:link-bold-duotone" class="inline text-xs text-accent" />
                      Campos com destino no Pipedrive são gravados no <strong class="text-neutral-400">Deal</strong> da conversa quando o objetivo é cumprido.
                    </p>
                  </div>

                  <!-- PASSO 3: Ação -->
                  <div class="space-y-2 border-t border-white/5 pt-4">
                    <div class="flex items-center gap-2 mb-1">
                      <span class="text-[10px] font-mono text-accent bg-accent/10 px-1.5 py-0.5">PASSO 3</span>
                      <label class="field-label mb-0">O que fazer quando a IA cumprir o objetivo?</label>
                    </div>
                    <p class="text-[10px] font-mono text-neutral-600 mb-1">
                      Escolha apenas uma ação, executada quando a IA concluir o objetivo.
                    </p>
                    <div class="space-y-2">
                      <label
                        v-for="opt in [
                          { value: 'deactivate_ai',      title: 'Pausar a IA (recomendado)', icon: 'solar:pause-circle-bold-duotone', desc: 'A IA para de responder, conversa fica aberta esperando alguém da equipe assumir manualmente.' },
                          { value: 'assign_to_user',     title: 'Encaminhar para um atendente', icon: 'solar:user-rounded-bold-duotone', desc: 'A IA para e a conversa é atribuída automaticamente a um atendente específico (você escolhe quem abaixo).' },
                          { value: 'close_conversation', title: 'Encerrar a conversa', icon: 'solar:close-circle-bold-duotone', desc: 'Marca a conversa como concluída/fechada. Use quando o objetivo for o atendimento completo sem precisar de humano.' },
                          { value: 'trigger_automation', title: 'Iniciar automação', icon: 'solar:settings-bold-duotone', desc: 'Dispara uma automação específica, escolhida abaixo (ex: enviar para webhook externo, enviar mensagem, pausar a IA).' },
                        ]"
                        :key="opt.value"
                        class="flex items-start gap-3 px-4 py-3 bg-canvas border cursor-pointer transition-colors"
                        :class="form.goal_action === opt.value ? 'border-accent/40 bg-accent/5' : 'border-white/5 hover:border-white/10'"
                      >
                        <input
                          type="radio"
                          v-model="form.goal_action"
                          :value="opt.value"
                          class="mt-1 accent-[rgb(var(--accent-rgb))] shrink-0"
                        />
                        <Icon :icon="opt.icon" class="text-lg text-neutral-400 shrink-0 mt-0.5" />
                        <div class="flex-1">
                          <p class="text-sm text-white font-medium">{{ opt.title }}</p>
                          <p class="text-[11px] font-mono text-neutral-600 mt-0.5 leading-relaxed">{{ opt.desc }}</p>
                        </div>
                      </label>
                    </div>
                  </div>

                  <!-- Select de operador (condicional) -->
                  <Transition name="fade">
                    <div v-if="form.goal_action === 'assign_to_user'" class="ml-2 pl-3 border-l-2 border-accent/30">
                      <label class="field-label">Para qual atendente encaminhar?</label>
                      <div class="bg-surface border border-white/10 rounded-full py-2.5 pl-5 pr-3 hover:border-accent/50 transition-colors">
                        <select v-model="form.goal_assign_to_id" class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer">
                          <option :value="null" class="bg-surface">— escolha um membro da organização —</option>
                          <option v-for="m in members" :key="m.id" :value="m.id" class="bg-surface">
                            {{ m.name || m.email }}
                          </option>
                        </select>
                      </div>
                      <p v-if="!members.length && !membersLoading" class="text-[10px] font-mono text-yellow-400/80 mt-1">
                        Nenhum membro encontrado — convide alguém para a organização primeiro.
                      </p>
                    </div>
                  </Transition>

                  <!-- Select de automação (condicional) -->
                  <Transition name="fade">
                    <div v-if="form.goal_action === 'trigger_automation'" class="ml-2 pl-3 border-l-2 border-accent/30">
                      <label class="field-label">Qual automação disparar?</label>
                      <div class="bg-surface border border-white/10 rounded-full py-2.5 pl-5 pr-3 hover:border-accent/50 transition-colors">
                        <select v-model="form.goal_automation_id" class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer">
                          <option :value="null" class="bg-surface">— escolha uma automação —</option>
                          <option v-for="a in goalAutomations" :key="a.id" :value="a.id" class="bg-surface">
                            {{ a.name }}
                          </option>
                        </select>
                      </div>
                      <p v-if="!goalAutomations.length" class="text-[10px] font-mono text-yellow-400/80 mt-1">
                        Nenhuma automação com gatilho "Objetivo do agente cumprido" — crie uma na aba Automações primeiro.
                      </p>
                      <p v-else class="text-[10px] font-mono text-neutral-700 mt-1">
                        Só a automação escolhida roda — sem conflito com outras.
                      </p>
                    </div>
                  </Transition>

                  <!-- PASSO 4: Mensagem final -->
                  <div class="border-t border-white/5 pt-4">
                    <div class="flex items-center gap-2 mb-1.5">
                      <span class="text-[10px] font-mono text-accent bg-accent/10 px-1.5 py-0.5">PASSO 4</span>
                      <label class="field-label mb-0">Mensagem de despedida da IA <span class="text-neutral-700 normal-case">(opcional)</span></label>
                    </div>
                    <div class="input-wrapper !py-0 !px-0">
                      <textarea
                        v-model="form.goal_final_message"
                        rows="2"
                        placeholder="Ex: Anotei tudo aqui! Vou te transferir para um atendente humano em instantes, ok?"
                        class="input-field resize-none !py-2.5 !px-3"
                      />
                    </div>
                    <p class="text-[10px] font-mono text-neutral-700 mt-1">
                      Enviada ao cliente via WhatsApp imediatamente antes da ação acima. Deixe em branco se não quiser nenhuma despedida.
                    </p>
                  </div>

                  <!-- Resumo final -->
                  <div class="bg-accent/5 border border-accent/20 px-4 py-3">
                    <p class="text-[10px] font-mono text-accent uppercase tracking-widest mb-1.5">Resumo do que vai acontecer</p>
                    <p class="text-[11px] font-mono text-accent/80 leading-relaxed">
                      A IA conversa normalmente até cumprir o objetivo descrito acima.
                      <template v-if="form.goal_slots.length"> Os dados coletados ({{ form.goal_slots.map(s => s.key).filter(Boolean).join(', ') || '—' }}) são salvos no contato.</template>
                      <template v-if="form.goal_final_message"> A IA envia a mensagem de despedida.</template>
                      <template v-if="form.goal_action === 'deactivate_ai'"> Depois a IA pausa.</template>
                      <template v-else-if="form.goal_action === 'assign_to_user'"> Depois a conversa é encaminhada ao atendente escolhido.</template>
                      <template v-else-if="form.goal_action === 'close_conversation'"> Depois a conversa é encerrada.</template>
                      <template v-else-if="form.goal_action === 'trigger_automation'"> Depois dispara a automação <strong>{{ goalAutomations.find(a => a.id === form.goal_automation_id)?.name || '— nenhuma escolhida —' }}</strong>.</template>
                      <template v-else><span class="text-red-300"> Escolha uma ação no PASSO 3.</span></template>
                    </p>
                  </div>
                </div>
              </Transition>

              <div v-if="!form.goal_enabled" class="flex flex-col items-center justify-center py-8 text-center">
                <Icon icon="solar:target-bold-duotone" class="text-3xl text-white/10 mb-2" />
                <p class="text-xs font-mono text-neutral-700">Objetivo desativado</p>
                <p class="text-[10px] font-mono text-neutral-700 mt-1 max-w-xs">
                  Ligue o toggle acima para configurar quando a IA deve parar e o que fazer ao concluir
                </p>
              </div>
            </div>

            <!-- ===================== ABA ENVIO ===================== -->
            <div v-else-if="tab === 'envio'" class="space-y-4">

              <div class="bg-blue-500/5 border border-blue-500/20 px-4 py-3">
                <div class="flex items-start gap-2">
                  <Icon icon="solar:info-circle-bold-duotone" class="text-base text-blue-400 shrink-0 mt-0.5" />
                  <p class="text-[11px] font-mono text-blue-200/80 leading-relaxed">
                    Controle como a IA recebe e responde mensagens: agrupe mensagens picadas do usuário em uma única chamada,
                    e divida respostas longas em várias bolhas no WhatsApp.
                  </p>
                </div>
              </div>

              <!-- ===== Acumular mensagens do usuário ===== -->
              <div class="flex items-center justify-between py-3 border-b border-white/5">
                <div>
                  <p class="text-sm text-white">Acumular mensagens do usuário</p>
                  <p class="text-[10px] font-mono text-neutral-600 mt-0.5">
                    Aguarda alguns segundos antes de processar, agrupando mensagens picadas em uma única resposta
                  </p>
                </div>
                <button
                  type="button"
                  @click="form.accumulate_messages_enabled = !form.accumulate_messages_enabled"
                  class="relative w-10 h-5 rounded-full transition-colors flex-shrink-0"
                  :class="form.accumulate_messages_enabled ? 'bg-accent' : 'bg-neutral-800'"
                >
                  <span
                    class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                    :class="form.accumulate_messages_enabled ? 'translate-x-5' : 'translate-x-0'"
                  ></span>
                </button>
              </div>

              <Transition name="fade">
                <div v-if="form.accumulate_messages_enabled" class="space-y-3">
                  <div>
                    <label class="field-label">Janela de espera <span class="text-neutral-700 normal-case">(segundos)</span></label>
                    <div class="input-wrapper">
                      <input
                        v-model.number="form.accumulate_window_seconds"
                        type="number" min="2" max="60" step="1"
                        class="input-field"
                      />
                    </div>
                    <p class="text-[10px] font-mono text-neutral-700 mt-1">
                      Recomendado 5–15s. Cada nova mensagem dentro da janela reinicia o contador.
                    </p>
                  </div>

                  <div class="bg-accent/5 border border-accent/20 px-4 py-3">
                    <p class="text-[11px] font-mono text-accent/80 leading-relaxed">
                      Exemplo: usuário envia "Oi", "tudo bem?", "como vc tá?" em 3 segundos.
                      A IA aguarda <strong class="text-accent">{{ form.accumulate_window_seconds }}s</strong> de silêncio
                      e processa as 3 mensagens juntas, gerando <strong class="text-accent">1 resposta</strong> em vez de 3.
                    </p>
                  </div>
                </div>
              </Transition>

              <!-- Toggle habilitar split -->
              <div class="flex items-center justify-between py-3 border-b border-white/5">
                <div>
                  <p class="text-sm text-white">Dividir resposta em mensagens</p>
                  <p class="text-[10px] font-mono text-neutral-600 mt-0.5">
                    Quebra por frase (. ? !) e envia uma mensagem por vez
                  </p>
                </div>
                <button
                  type="button"
                  @click="form.split_messages_enabled = !form.split_messages_enabled"
                  class="relative w-10 h-5 rounded-full transition-colors flex-shrink-0"
                  :class="form.split_messages_enabled ? 'bg-accent' : 'bg-neutral-800'"
                >
                  <span
                    class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                    :class="form.split_messages_enabled ? 'translate-x-5' : 'translate-x-0'"
                  ></span>
                </button>
              </div>

              <Transition name="fade">
                <div v-if="form.split_messages_enabled" class="space-y-4">

                  <div>
                    <label class="field-label">Velocidade de digitação <span class="text-neutral-700 normal-case">(ms por caractere)</span></label>
                    <div class="input-wrapper">
                      <input
                        v-model.number="form.split_typing_speed_ms_per_char"
                        type="number" min="10" max="80"
                        class="input-field"
                      />
                    </div>
                    <p class="text-[10px] font-mono text-neutral-700 mt-1">
                      Menor = digita mais rápido. Padrão 35ms (~280 chars/seg).
                    </p>
                  </div>

                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="field-label">Delay mínimo <span class="text-neutral-700 normal-case">(ms)</span></label>
                      <div class="input-wrapper">
                        <input
                          v-model.number="form.split_min_delay_ms"
                          type="number" min="100" max="10000" step="100"
                          class="input-field"
                        />
                      </div>
                      <p class="text-[10px] font-mono text-neutral-700 mt-1">Pausa mínima entre mensagens</p>
                    </div>
                    <div>
                      <label class="field-label">Delay máximo <span class="text-neutral-700 normal-case">(ms)</span></label>
                      <div class="input-wrapper">
                        <input
                          v-model.number="form.split_max_delay_ms"
                          type="number" min="500" max="20000" step="100"
                          class="input-field"
                        />
                      </div>
                      <p class="text-[10px] font-mono text-neutral-700 mt-1">Pausa máxima entre mensagens</p>
                    </div>
                  </div>

                  <div class="bg-accent/5 border border-accent/20 px-4 py-3">
                    <p class="text-[11px] font-mono text-accent/80 leading-relaxed">
                      Exemplo: resposta "Boa noite! Tudo bem? Como posso ajudar?" será enviada em
                      <strong class="text-accent">3 mensagens</strong>, com pausa de
                      <strong class="text-accent">{{ form.split_min_delay_ms }}–{{ form.split_max_delay_ms }}ms</strong>
                      entre elas, proporcional ao tamanho da próxima frase.
                    </p>
                  </div>
                </div>
              </Transition>

              <div v-if="!form.split_messages_enabled" class="flex flex-col items-center justify-center py-8 text-center">
                <Icon icon="solar:chat-line-bold-duotone" class="text-3xl text-white/10 mb-2" />
                <p class="text-xs font-mono text-neutral-700">Envio em mensagem única</p>
                <p class="text-[10px] font-mono text-neutral-700 mt-1 max-w-xs">
                  A IA envia a resposta inteira em uma só bolha do WhatsApp
                </p>
              </div>
            </div>

          </div>

          <!-- Rodapé fixo -->
          <div class="px-6 py-4 border-t border-white/5 shrink-0">
            <p v-if="error" class="text-xs font-mono text-red-400 mb-3">{{ error }}</p>
            <div class="flex gap-3">
              <button
                type="button"
                @click="emit('close')"
                class="flex-1 py-2.5 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                :disabled="loading || providers.length === 0"
                @click="submit"
                class="btn-primary flex-1 disabled:opacity-50"
              >
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">
                  {{ loading ? 'Salvando…' : isEdit ? 'Salvar' : 'Criar' }}
                </span>
              </button>
            </div>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

<style>
.md-editor {
  --md-bk-color: var(--base) !important;
  --md-border-color: var(--border-md) !important;
  border-radius: 0 !important;
  font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
}
.md-editor-toolbar-wrapper {
  background: var(--surface) !important;
  border-bottom: 1px solid var(--border) !important;
}
.md-editor-toolbar-item:hover {
  color: rgb(var(--accent-rgb)) !important;
  background: rgb(var(--accent-rgb) / 0.08) !important;
}
.md-editor-input-wrapper textarea {
  font-size: 13px !important;
  line-height: 1.6 !important;
}
.md-editor-fullscreen {
  z-index: 9999 !important;
}
</style>
