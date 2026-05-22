<script setup lang="ts">
import { Icon } from '@iconify/vue'

const props = defineProps<{ conversation: any; showBack?: boolean }>()
const emit = defineEmits<{ updated: [conv: any]; back: []; deleted: [id: number] }>()

const api = useApi()

const messages = ref<any[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(false)
const text = ref('')
const sending = ref(false)
const showStickerPicker = ref(false)
const stickers = ref<any[]>([])
const fileInputRef = ref<HTMLInputElement>()
const messagesEndRef = ref<HTMLDivElement>()

const conv = ref({ ...props.conversation })
watch(() => props.conversation, (val) => { conv.value = { ...val } }, { deep: true })

const selectedInstanceId = ref<number | null>(conv.value.instance_id || null)
const instances = ref<any[]>([])
const agents = ref<any[]>([])
const showInstanceSelector = ref(false)
const selectedInstance = computed(() => instances.value.find((i: any) => i.id === selectedInstanceId.value) || null)
const addInstanceId = (url: string) => {
  if (!selectedInstanceId.value) return url
  return url + (url.includes('?') ? '&' : '?') + 'instance_id=' + selectedInstanceId.value
}

const authStore = useAuthStore()
const config = useRuntimeConfig()
let ws: WebSocket | null = null
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

const fetchMessages = async () => {
  try {
    const data = await api<any[]>(`/api/conversations/${conv.value.id}/messages?limit=50`)
    messages.value = data
    hasMore.value = data.length >= 50
  } catch {}
}

const messagesContainerRef = ref<HTMLDivElement>()

const onMessagesScroll = () => {
  const el = messagesContainerRef.value
  if (el && el.scrollTop < 80) loadOlderMessages()
}

const loadOlderMessages = async () => {
  if (!hasMore.value || loadingMore.value || !messages.value.length) return
  loadingMore.value = true
  try {
    const beforeId = messages.value[0].id
    const older = await api<any[]>(`/api/conversations/${conv.value.id}/messages?limit=50&before_id=${beforeId}`)
    if (!older.length) {
      hasMore.value = false
      return
    }
    const container = messagesContainerRef.value
    const prevScrollHeight = container?.scrollHeight ?? 0
    const existingIds = new Set(messages.value.map((m: any) => m.id))
    const unique = older.filter((m: any) => !existingIds.has(m.id))
    messages.value = [...unique, ...messages.value]
    hasMore.value = unique.length >= 50
    await nextTick()
    if (container) container.scrollTop = container.scrollHeight - prevScrollHeight
  } catch {} finally {
    loadingMore.value = false
  }
}

const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
  nextTick(() => {
    messagesEndRef.value?.scrollIntoView({ behavior })
  })
}

const connectWs = () => {
  if (!authStore.accessToken) return

  const wsBase = config.public.apiBase.replace(/^http/, 'ws')
  const wsUrl = `${wsBase}/ws/conversations/${conv.value.id}/?token=${authStore.accessToken}`
  ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    const payload = JSON.parse(event.data)
    if (payload.type === 'new_message') {
      const idx = messages.value.findIndex(m => m.id === payload.message.id)
      if (idx !== -1) {
        // Atualiza mensagem existente (ex: scheduled_status pending → sent)
        messages.value[idx] = { ...messages.value[idx], ...payload.message }
      } else {
        messages.value.push(payload.message)
        scrollToBottom()
      }
    } else if (payload.type === 'attachment_updated') {
      const { message_id, id, transcription, transcription_status } = payload.attachment
      const msg = messages.value.find(m => m.id === message_id)
      if (msg) {
        const att = msg.attachments?.find((a: any) => a.id === id)
        if (att) {
          att.transcription = transcription
          att.transcription_status = transcription_status
        }
      }
    } else if (payload.type === 'conversation_updated') {
      conv.value = { ...conv.value, ...payload.conversation }
      emit('updated', { ...conv.value })
    }
  }

  ws.onclose = async (event) => {
    if (event.code === 4001) {
      // Token expirado — tenta renovar e reconectar
      const refreshed = await authStore.refresh()
      if (refreshed) connectWs()
      return
    }
    if (event.code === 4003) return  // Sem acesso à conversa
    // Reconecta após 3s se o componente ainda estiver montado
    reconnectTimeout = setTimeout(() => {
      if (ws) connectWs()
    }, 3000)
  }

  ws.onerror = () => ws?.close()
}

// --- Templates ---
const templates = ref<any[]>([])
const showTemplatePicker = ref(false)
const templateQuery = ref('')

const fetchTemplates = async () => {
  try {
    templates.value = await api<any[]>('/api/templates/')
  } catch {}
}

const onTextInput = (e: Event) => {
  const t = e.target as HTMLTextAreaElement
  t.style.height = 'auto'
  t.style.height = t.scrollHeight + 'px'

  const val = text.value
  if (val.startsWith('/')) {
    templateQuery.value = val.slice(1)
    showTemplatePicker.value = true
  } else {
    showTemplatePicker.value = false
    templateQuery.value = ''
  }
}

const onTemplateSelectText = (template: any) => {
  text.value = template.content
  showTemplatePicker.value = false
  templateQuery.value = ''
}

const onTemplateSelectMedia = async (template: any) => {
  showTemplatePicker.value = false
  templateQuery.value = ''
  text.value = ''
  try {
    const msg = await api<any>(
      addInstanceId(`/api/conversations/${conv.value.id}/messages/from-template?template_id=${template.id}`),
      { method: 'POST' }
    )
    if (!messages.value.some(m => m.id === msg.id)) messages.value.push(msg)
    conv.value.ai_active = false
    emit('updated', { ...conv.value })
    scrollToBottom()
  } catch (e) {
    console.error(e)
  }
}

onMounted(async () => {
  await fetchMessages()
  await fetchTemplates()
  try { instances.value = await api<any[]>('/api/integrations/whatsapp/') } catch {}
  try { agents.value = await api<any[]>('/api/agents/') } catch {}
  loading.value = false
  scrollToBottom('instant')
  connectWs()
})

onUnmounted(() => {
  if (reconnectTimeout) clearTimeout(reconnectTimeout)
  if (ws) { ws.onclose = null; ws.close() }
  ws = null
})

// --- Envio de texto ---
const sendText = async () => {
  if (!text.value.trim() || sending.value) return
  sending.value = true
  const content = text.value.trim()
  const scheduled = scheduledAt.value
  text.value = ''
  scheduledAt.value = ''
  showScheduler.value = false
  try {
    const body: any = { content }
    if (scheduled) body.scheduled_at = new Date(scheduled).toISOString()
    const msg = await api<any>(addInstanceId(`/api/conversations/${conv.value.id}/messages`), {
      method: 'POST',
      body,
    })
    const existingIdx = messages.value.findIndex(m => m.id === msg.id)
    if (existingIdx !== -1) {
      // WS chegou antes — atualiza com os dados completos do REST (incluindo scheduled_status)
      messages.value[existingIdx] = { ...messages.value[existingIdx], ...msg }
    } else {
      messages.value.push(msg)
    }
    if (!scheduled) {
      conv.value.ai_active = false
      emit('updated', { ...conv.value })
    }
    scrollToBottom()
  } catch (e) {
    text.value = content
    scheduledAt.value = scheduled
    console.error(e)
  } finally {
    sending.value = false
  }
}

const onKeydown = (e: KeyboardEvent) => {
  // Quando o picker está aberto, Enter/ArrowUp/ArrowDown/Escape são tratados pelo TemplatePicker
  if (showTemplatePicker.value && ['Enter', 'ArrowUp', 'ArrowDown', 'Escape'].includes(e.key)) return
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendText()
  }
}

// --- Envio de mídia ---
const getMediaType = (file: File): string => {
  if (file.type === 'image/gif') return 'gif'
  if (file.type.startsWith('image/')) return 'image'
  if (file.type.startsWith('audio/')) return 'audio'
  if (file.type.startsWith('video/')) return 'video'
  return 'document'
}

const onFileChange = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = ''

  const mediaType = getMediaType(file)
  const formData = new FormData()
  formData.append('file', file)
  formData.append('media_type', mediaType)
  formData.append('caption', '')

  try {
    const msg = await api<any>(addInstanceId(`/api/conversations/${conv.value.id}/messages/media`), {
      method: 'POST',
      body: formData,
    })
    if (!messages.value.some(m => m.id === msg.id)) messages.value.push(msg)
    conv.value.ai_active = false
    emit('updated', { ...conv.value })
    scrollToBottom()
  } catch (e) {
    console.error(e)
  }
}

// --- Figurinhas ---
const fetchStickers = async () => {
  if (stickers.value.length > 0) return
  try {
    stickers.value = await api<any[]>('/api/conversations/stickers')
  } catch {}
}

const openStickerPicker = () => {
  fetchStickers()
  showStickerPicker.value = !showStickerPicker.value
}

const savedAttachmentIds = ref<Set<number>>(new Set())

// --- Gravação de áudio ---
const isRecording = ref(false)
const recordingSeconds = ref(0)
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let recordingTimer: ReturnType<typeof setInterval> | null = null

const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    recordingSeconds.value = 0
    const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/ogg'
    mediaRecorder = new MediaRecorder(stream, { mimeType })
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
    mediaRecorder.onstop = () => {
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(audioChunks, { type: mimeType })
      sendAudioBlob(blob, mimeType)
    }
    mediaRecorder.start()
    isRecording.value = true
    recordingTimer = setInterval(() => recordingSeconds.value++, 1000)
  } catch (e) {
    console.error('[REC] Erro ao acessar microfone:', e)
  }
}

const stopRecording = () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop()
  if (recordingTimer) { clearInterval(recordingTimer); recordingTimer = null }
  isRecording.value = false
}

const cancelRecording = () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.ondataavailable = null
    mediaRecorder.onstop = null
    mediaRecorder.stop()
    mediaRecorder.stream?.getTracks().forEach(t => t.stop())
  }
  if (recordingTimer) { clearInterval(recordingTimer); recordingTimer = null }
  isRecording.value = false
  audioChunks = []
}

const sendAudioBlob = async (blob: Blob, mimeType: string) => {
  const ext = mimeType.includes('webm') ? 'webm' : 'ogg'
  const file = new File([blob], `audio.${ext}`, { type: mimeType })
  const formData = new FormData()
  formData.append('file', file)
  formData.append('media_type', 'audio')
  formData.append('caption', '')
  try {
    const msg = await api<any>(addInstanceId(`/api/conversations/${conv.value.id}/messages/media`), {
      method: 'POST',
      body: formData,
    })
    if (!messages.value.some(m => m.id === msg.id)) messages.value.push(msg)
    conv.value.ai_active = false
    emit('updated', { ...conv.value })
    scrollToBottom()
  } catch (e) {
    console.error(e)
  }
}

const formatRecordingTime = (s: number) => {
  const m = Math.floor(s / 60).toString().padStart(2, '0')
  const sec = (s % 60).toString().padStart(2, '0')
  return `${m}:${sec}`
}

const saveSticker = async (att: any) => {
  if (savedAttachmentIds.value.has(att.id)) return
  try {
    const sticker = await api<any>(`/api/conversations/stickers/from-attachment/${att.id}`, {
      method: 'POST',
    })
    stickers.value.unshift(sticker)
    savedAttachmentIds.value = new Set([...savedAttachmentIds.value, att.id])
  } catch (e) {
    console.error(e)
  }
}

const deleteSticker = async (sticker: any) => {
  try {
    await api(`/api/conversations/stickers/${sticker.id}`, { method: 'DELETE' })
    stickers.value = stickers.value.filter(s => s.id !== sticker.id)
  } catch (e) {
    console.error(e)
  }
}

const sendSticker = async (sticker: any) => {
  showStickerPicker.value = false
  try {
    const msg = await api<any>(addInstanceId(`/api/conversations/${conv.value.id}/messages/sticker`), {
      method: 'POST',
      body: { sticker_id: sticker.id },
    })
    if (!messages.value.some(m => m.id === msg.id)) messages.value.push(msg)
    conv.value.ai_active = false
    emit('updated', { ...conv.value })
    scrollToBottom()
  } catch (e) {
    console.error(e)
  }
}

// --- Editar contato ---
type Field = { key: string; value: string }

const dictToFields = (dict: Record<string, any>): Field[] =>
  Object.entries(dict ?? {}).map(([key, value]) => ({ key, value: String(value ?? '') }))

const fieldsToDct = (fields: Field[]): Record<string, string> =>
  Object.fromEntries(fields.filter(f => f.key.trim()).map(f => [f.key.trim(), f.value]))

const editingContact = ref(false)
const editContactFetching = ref(false)
const editContactForm = reactive({
  name: '',
  phone: '',
  email: '',
  customFields: [] as Field[],
})
const editContactLoading = ref(false)
const editContactError = ref('')

const openEditContact = async () => {
  // Abre imediatamente com o que temos (nome/telefone da conversa)
  editContactForm.name = conv.value.contact.name ?? ''
  editContactForm.phone = conv.value.contact.phone ?? ''
  editContactForm.email = ''
  editContactForm.customFields = []
  editContactError.value = ''
  editingContact.value = true
  editContactFetching.value = true

  // Busca contato completo (custom_fields não vem no schema de conversas)
  try {
    const full = await api<any>(`/api/contacts/${conv.value.contact.id}`)
    editContactForm.name = full.name ?? ''
    editContactForm.phone = full.phone ?? ''
    editContactForm.email = full.email ?? ''
    editContactForm.customFields = dictToFields(full.custom_fields)
    // Enriquece o contato local para evitar re-fetch na próxima abertura
    conv.value = { ...conv.value, contact: { ...conv.value.contact, ...full } }
  } catch {}
  finally { editContactFetching.value = false }
}

const addContactField = () => editContactForm.customFields.push({ key: '', value: '' })
const removeContactField = (i: number) => editContactForm.customFields.splice(i, 1)

const saveContact = async () => {
  editContactLoading.value = true
  editContactError.value = ''
  try {
    const updated = await api<any>(`/api/contacts/${conv.value.contact.id}`, {
      method: 'PATCH',
      body: {
        name: editContactForm.name,
        phone: editContactForm.phone,
        email: editContactForm.email,
        custom_fields: fieldsToDct(editContactForm.customFields),
      },
    })
    conv.value = { ...conv.value, contact: updated }
    emit('updated', { ...conv.value })
    editingContact.value = false
  } catch (e: any) {
    editContactError.value = e?.data?.detail || 'Erro ao salvar contato'
  } finally {
    editContactLoading.value = false
  }
}

// --- Atribuição de responsável ---
const orgMembers = ref<any[]>([])
const loadingMembers = ref(false)
const showAssignPanel = ref(false)
const assignSearch = ref('')
const assignLoading = ref(false)

const filteredMembers = computed(() =>
  orgMembers.value.filter(m =>
    m.name?.toLowerCase().includes(assignSearch.value.toLowerCase()) ||
    m.email?.toLowerCase().includes(assignSearch.value.toLowerCase())
  )
)

const fetchOrgMembers = async () => {
  if (orgMembers.value.length) return
  loadingMembers.value = true
  try { orgMembers.value = await api<any[]>('/api/org/members') }
  catch {} finally { loadingMembers.value = false }
}

const openAssignPanel = async () => {
  assignSearch.value = ''
  showAssignPanel.value = true
  await fetchOrgMembers()
}

const assignUser = async (userId: number | null) => {
  assignLoading.value = true
  try {
    const updated = await api<any>(`/api/conversations/${conv.value.id}`, {
      method: 'PATCH',
      body: { assigned_to_id: userId },
    })
    conv.value.assigned_to_id = updated.assigned_to_id
    conv.value.assigned_to_name = updated.assigned_to_name
    emit('updated', { ...conv.value })
    showAssignPanel.value = false
  } catch {} finally { assignLoading.value = false }
}

// --- Ações da conversa ---
const canDeleteConversation = computed(() => {
  const role = authStore.user?.role
  if (role === 'owner' || role === 'admin') return true
  return authStore.user?.permissions?.can_delete_conversations ?? false
})

const canClearMemory = computed(() => {
  const role = authStore.user?.role
  return role === 'owner' || role === 'admin'
})

const { confirm: confirmDialog } = useConfirm()

const clearMemory = async () => {
  const ok = await confirmDialog(
    'A IA passará a ignorar todas as mensagens anteriores desta conversa. O histórico continua visível no chat.',
    { title: 'Apagar memória da IA?' },
  )
  if (!ok) return
  try {
    await api(`/api/conversations/${conv.value.id}/clear-memory`, { method: 'POST' })
  } catch {}
}

const deleteConversation = async () => {
  const ok = await confirmDialog('Esta ação não pode ser desfeita.', { title: 'Excluir conversa?' })
  if (!ok) return
  try {
    await api(`/api/conversations/${conv.value.id}`, { method: 'DELETE' })
    emit('deleted', conv.value.id)
  } catch {}
}

const toggleAI = async () => {
  try {
    const updated = await api<any>(`/api/conversations/${conv.value.id}`, {
      method: 'PATCH',
      body: { ai_active: !conv.value.ai_active },
    })
    conv.value.ai_active = updated.ai_active
    emit('updated', { ...conv.value })
  } catch {}
}

const switchAgent = async (e: Event) => {
  const agentId = Number((e.target as HTMLSelectElement).value)
  try {
    const updated = await api<any>(`/api/conversations/${conv.value.id}`, {
      method: 'PATCH',
      body: { agent_id: agentId },
    })
    conv.value.agent_id = updated.agent_id
    conv.value.agent_name = updated.agent_name
    emit('updated', { ...conv.value })
  } catch {}
}

const toggleStatus = async () => {
  const newStatus = conv.value.status === 'open' ? 'closed' : 'open'
  try {
    const updated = await api<any>(`/api/conversations/${conv.value.id}`, {
      method: 'PATCH',
      body: { status: newStatus },
    })
    conv.value.status = updated.status
    emit('updated', { ...conv.value })
  } catch {}
}

// --- Etiquetas ---
const showLabels = ref(false)

const onLabelsUpdated = (labels: any[]) => {
  conv.value = { ...conv.value, labels }
  emit('updated', { ...conv.value })
}

// --- Anotações ---
const showAnnotations = ref(false)

// --- Pipedrive ---
const showPipedrive = ref(false)

// --- Agendamento ---
const scheduledAt = ref('')
const showScheduler = ref(false)
const minDatetime = computed(() => new Date(Date.now() + 60_000).toISOString().slice(0, 16))

const formatScheduled = (dt: string) =>
  new Date(dt).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

// --- Helpers ---
const formatTime = (dt: string) =>
  new Date(dt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })

const isOperator = (role: string) => role === 'operator'

const formatDateSeparator = (dt: string) => {
  const d = new Date(dt)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)
  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
  if (sameDay(d, today)) return 'Hoje'
  if (sameDay(d, yesterday)) return 'Ontem'
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })
}

const isDifferentDay = (a: string, b: string) => {
  const da = new Date(a), db = new Date(b)
  return da.getFullYear() !== db.getFullYear() || da.getMonth() !== db.getMonth() || da.getDate() !== db.getDate()
}

const followUpLabel = computed(() => {
  if (!conv.value.ai_active || !conv.value.agent_id) return null
  const count = conv.value.follow_up_count || 0
  const next = conv.value.next_follow_up_at
  if (!next) return null
  const nextDt = new Date(next)
  const now = new Date()
  const diffMs = nextDt.getTime() - now.getTime()
  const diffMin = Math.round(diffMs / 60000)
  const timeStr = diffMin <= 0
    ? 'agora'
    : diffMin < 60
      ? `em ${diffMin}min`
      : nextDt.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
  return { count, timeStr }
})

const roleLabel = (role: string, msg?: any) => {
  if (role === 'user') return conv.value.contact?.name || 'Cliente'
  if (role === 'assistant') return conv.value.agent_name || 'IA'
  if (role === 'operator') return msg?.sent_by_name || authStore.user?.name || 'Operador'
  if (role === 'system') return 'Sistema'
  return role
}
</script>

<template>
  <div class="relative flex flex-col h-full bg-canvas overflow-hidden">
    <!-- Top bar -->
    <div class="flex items-center justify-between px-3 sm:px-6 py-3 sm:py-4 border-b border-white/5 bg-surface shrink-0 gap-2">
      <div class="flex items-center gap-2 min-w-0">
        <!-- Botão voltar (mobile) -->
        <button
          v-if="showBack"
          @click="emit('back')"
          class="p-1 text-neutral-400 hover:text-white transition-colors shrink-0"
          title="Voltar"
        >
          <Icon icon="solar:arrow-left-bold-duotone" class="text-base" />
        </button>
        <div class="min-w-0">
          <p class="text-sm font-medium text-white truncate">{{ conv.contact.name }}</p>
          <p class="text-[11px] font-mono text-neutral-600 hidden sm:block">{{ conv.contact.phone }}</p>
        </div>
        <button
          @click="openEditContact"
          class="p-1 text-neutral-600 hover:text-neutral-300 transition-colors shrink-0"
          title="Editar contato"
        >
          <Icon icon="solar:pen-bold-duotone" class="text-sm" />
        </button>
      </div>

      <div class="flex items-center gap-1.5 shrink-0">
        <!-- Badge status — só desktop -->
        <span
          class="hidden sm:inline text-[9px] font-mono uppercase tracking-widest px-2 py-1"
          :class="conv.status === 'open' ? 'text-green-400 bg-green-400/10' : 'text-neutral-500 bg-white/5'"
        >
          {{ conv.status === 'open' ? 'Aberta' : 'Fechada' }}
        </span>

        <!-- Responsável -->
        <button
          @click="openAssignPanel"
          class="flex items-center gap-1 px-2 sm:px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest border transition-colors"
          :class="conv.assigned_to_id
            ? 'border-white/20 text-neutral-300'
            : 'border-white/10 text-neutral-500 hover:border-white/20 hover:text-neutral-300'"
          :title="conv.assigned_to_name ? `Responsável: ${conv.assigned_to_name}` : 'Atribuir responsável'"
        >
          <Icon icon="solar:user-bold-duotone" class="text-sm" />
          <span class="hidden sm:inline max-w-[80px] truncate">
            {{ conv.assigned_to_name ? conv.assigned_to_name.split(' ')[0] : 'Atribuir' }}
          </span>
        </button>

        <!-- Toggle IA -->
        <button
          @click="toggleAI"
          class="flex items-center gap-1 px-2 sm:px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest border transition-colors"
          :class="conv.ai_active && conv.agent_id
            ? 'border-accent/30 text-accent bg-accent/5 hover:bg-accent/10'
            : 'border-white/10 text-neutral-500 hover:border-white/20 hover:text-neutral-300'"
          :title="conv.ai_active ? 'Desativar IA' : 'Ativar IA'"
        >
          <Icon icon="solar:cpu-bolt-bold-duotone" class="text-sm" />
          <span class="hidden sm:inline">IA {{ conv.ai_active ? 'on' : 'off' }}</span>
        </button>

        <!-- Trocar agente da conversa -->
        <select
          :value="conv.agent_id || 0"
          @change="switchAgent"
          class="px-2 py-1.5 text-[10px] font-mono uppercase tracking-widest bg-canvas border border-white/10 text-neutral-300 outline-none focus:border-white/20 max-w-[140px]"
          title="Agente desta conversa"
        >
          <option :value="0">Agente oficial</option>
          <option v-for="a in agents" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>

        <!-- Fechar/Reabrir -->
        <button
          @click="toggleStatus"
          class="flex items-center gap-1 px-2 sm:px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest border transition-colors"
          :class="conv.status === 'open'
            ? 'border-white/10 text-neutral-500 hover:border-red-500/30 hover:text-red-400'
            : 'border-white/10 text-neutral-500 hover:border-green-500/30 hover:text-green-400'"
        >
          <Icon
            :icon="conv.status === 'open' ? 'solar:close-circle-bold-duotone' : 'solar:restart-bold-duotone'"
            class="text-sm"
          />
          <span class="hidden sm:inline">{{ conv.status === 'open' ? 'Fechar' : 'Reabrir' }}</span>
        </button>

        <!-- Etiquetas -->
        <button
          @click="showLabels = !showLabels"
          class="px-2 py-1.5 border transition-colors"
          :class="showLabels
            ? 'border-accent/30 text-accent bg-accent/5'
            : 'border-white/10 text-neutral-500 hover:border-white/20 hover:text-neutral-300'"
          title="Etiquetas"
        >
          <Icon icon="solar:tag-bold-duotone" class="text-sm" />
        </button>

        <!-- Anotações -->
        <button
          @click="showAnnotations = !showAnnotations"
          class="px-2 py-1.5 border transition-colors"
          :class="showAnnotations
            ? 'border-accent/30 text-accent bg-accent/5'
            : 'border-white/10 text-neutral-500 hover:border-white/20 hover:text-neutral-300'"
          title="Anotações"
        >
          <Icon icon="solar:notebook-bold-duotone" class="text-sm" />
        </button>

        <!-- Pipedrive -->
        <button
          v-if="conv.pipedrive_deal_id"
          @click="showPipedrive = !showPipedrive"
          class="px-2 py-1.5 border transition-colors"
          :class="showPipedrive
            ? 'border-accent/30 text-accent bg-accent/5'
            : 'border-white/10 text-neutral-500 hover:border-white/20 hover:text-neutral-300'"
          title="Pipedrive"
        >
          <Icon icon="solar:case-round-bold-duotone" class="text-sm" />
        </button>

        <!-- Apagar memória da IA -->
        <button
          v-if="canClearMemory"
          @click="clearMemory"
          class="px-2 py-1.5 border border-white/10 text-neutral-500 hover:border-amber-500/30 hover:text-amber-400 transition-colors"
          title="Apagar memória da IA"
        >
          <Icon icon="solar:eraser-bold-duotone" class="text-sm" />
        </button>

        <!-- Excluir conversa -->
        <button
          v-if="canDeleteConversation"
          @click="deleteConversation"
          class="px-2 py-1.5 border border-white/10 text-neutral-500 hover:border-red-500/30 hover:text-red-400 transition-colors"
          title="Excluir conversa"
        >
          <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-sm" />
        </button>
      </div>
    </div>

    <!-- Painel editar contato -->
    <Transition name="scheduler">
      <div v-if="editingContact" class="border-b border-white/5 bg-canvas shrink-0">
        <div class="px-6 py-4">
          <div class="flex items-center justify-between mb-3">
            <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500">Editar contato</p>
            <div v-if="editContactFetching" class="w-3 h-3 border border-accent/30 border-t-accent rounded-full animate-spin"></div>
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="field-label">Nome</label>
              <input
                v-model="editContactForm.name"
                type="text"
                placeholder="Nome do contato"
                class="w-full bg-surface border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20 placeholder-neutral-700"
              />
            </div>
            <div>
              <label class="field-label">Telefone</label>
              <input
                v-model="editContactForm.phone"
                type="text"
                placeholder="5511999999999"
                class="w-full bg-surface border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20 placeholder-neutral-700"
              />
            </div>
            <div>
              <label class="field-label">E-mail</label>
              <input
                v-model="editContactForm.email"
                type="email"
                placeholder="email@exemplo.com"
                class="w-full bg-surface border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20 placeholder-neutral-700"
              />
            </div>
          </div>
          <!-- Campos personalizados -->
          <div class="mt-4 pt-3 border-t border-white/5">
            <div class="flex items-center justify-between mb-2">
              <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-600">Campos personalizados</p>
              <button
                type="button"
                @click="addContactField"
                class="text-[10px] font-mono text-accent hover:text-orange-300 transition-colors flex items-center gap-1"
              >
                <Icon icon="solar:add-circle-bold-duotone" class="text-xs" />
                Adicionar
              </button>
            </div>
            <div v-if="editContactForm.customFields.length === 0" class="py-2">
              <p class="text-[11px] font-mono text-neutral-700">Nenhum campo personalizado.</p>
            </div>
            <div v-else class="space-y-2">
              <div
                v-for="(f, i) in editContactForm.customFields"
                :key="i"
                class="flex items-center gap-2"
              >
                <input
                  v-model="f.key"
                  type="text"
                  placeholder="Label"
                  class="w-2/5 bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20 placeholder-neutral-700"
                />
                <input
                  v-model="f.value"
                  type="text"
                  placeholder="Valor"
                  class="flex-1 bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20 placeholder-neutral-700"
                />
                <button
                  type="button"
                  @click="removeContactField(i)"
                  class="p-1 text-neutral-600 hover:text-red-400 transition-colors shrink-0"
                >
                  <Icon icon="solar:close-circle-bold-duotone" class="text-xs" />
                </button>
              </div>
            </div>
          </div>

          <p v-if="editContactError" class="text-xs font-mono text-red-400 mt-2">{{ editContactError }}</p>
          <div class="flex items-center gap-2 mt-3">
            <button
              @click="saveContact"
              :disabled="editContactLoading"
              class="px-4 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-accent/30 text-accent hover:bg-accent/5 transition-colors disabled:opacity-50"
            >
              {{ editContactLoading ? 'Salvando...' : 'Salvar' }}
            </button>
            <button
              @click="editingContact = false"
              class="px-4 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-white/10 text-neutral-400 hover:border-white/20 hover:text-white transition-colors"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Painel de atribuição -->
    <Transition name="scheduler">
      <div v-if="showAssignPanel" class="border-b border-white/5 bg-canvas shrink-0">
        <div class="px-6 py-4">
          <div class="flex items-center justify-between mb-3">
            <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500">Responsável</p>
            <button @click="showAssignPanel = false" class="text-neutral-600 hover:text-neutral-300 transition-colors">
              <Icon icon="solar:close-circle-bold-duotone" class="text-sm" />
            </button>
          </div>
          <input
            v-model="assignSearch"
            type="text"
            placeholder="Buscar membro..."
            class="w-full bg-surface border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20 placeholder-neutral-700 mb-3"
          />
          <button
            v-if="conv.assigned_to_id"
            @click="assignUser(null)"
            :disabled="assignLoading"
            class="w-full flex items-center gap-2.5 px-3 py-2 text-neutral-500 hover:text-red-400 hover:bg-white/5 transition-colors mb-1"
          >
            <Icon icon="solar:close-circle-bold-duotone" class="text-base shrink-0" />
            <span class="font-mono text-xs uppercase tracking-wider">Remover responsável</span>
          </button>
          <div class="max-h-48 overflow-y-auto space-y-px">
            <div v-if="loadingMembers" class="py-4 flex justify-center">
              <div class="w-4 h-4 border border-accent/30 border-t-accent rounded-full animate-spin"></div>
            </div>
            <button
              v-for="member in filteredMembers"
              :key="member.id"
              @click="assignUser(member.id)"
              :disabled="assignLoading"
              class="w-full flex items-center gap-2.5 px-3 py-2 text-sm transition-colors hover:bg-white/5"
              :class="conv.assigned_to_id === member.id ? 'text-accent' : 'text-neutral-300'"
            >
              <div class="w-6 h-6 shrink-0 bg-neutral-800 border border-white/10 flex items-center justify-center">
                <span class="text-[10px] font-mono text-neutral-400 uppercase">{{ member.name?.[0] }}</span>
              </div>
              <div class="min-w-0 text-left">
                <p class="text-xs font-medium truncate">{{ member.name }}</p>
                <p class="text-[10px] font-mono text-neutral-600 truncate">{{ member.role }}</p>
              </div>
              <Icon v-if="conv.assigned_to_id === member.id" icon="solar:check-circle-bold-duotone" class="text-accent text-sm ml-auto shrink-0" />
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Painel de etiquetas -->
    <Transition name="scheduler">
      <div v-if="showLabels" class="border-b border-white/5 bg-canvas shrink-0">
        <div class="px-6 py-4">
          <div class="flex items-center justify-between mb-3">
            <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500">Etiquetas</p>
            <button @click="showLabels = false" class="text-neutral-600 hover:text-neutral-300 transition-colors">
              <Icon icon="solar:close-circle-bold-duotone" class="text-sm" />
            </button>
          </div>
          <LabelsLabelSelector
            entity-type="conversation"
            :entity-id="conv.id"
            :labels="conv.labels ?? []"
            @updated="onLabelsUpdated"
          />
        </div>
      </div>
    </Transition>

    <!-- Follow-up indicator -->
    <div
      v-if="followUpLabel"
      class="flex items-center gap-2 px-4 py-1.5 bg-accent/5 border-b border-accent/10 text-[10px] font-mono text-accent/70"
    >
      <Icon icon="solar:alarm-bold-duotone" class="text-xs shrink-0" />
      <span>follow-up {{ followUpLabel.count }} — próximo {{ followUpLabel.timeStr }}</span>
    </div>

    <!-- Mensagens -->
    <div ref="messagesContainerRef" class="flex-1 overflow-y-auto scrollbar-thin px-6 py-5 space-y-3" @scroll.passive="onMessagesScroll">
      <div v-if="loading" class="flex items-center justify-center h-full">
        <div class="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin"></div>
      </div>

      <template v-else>
        <div v-if="loadingMore" class="flex justify-center py-2">
          <div class="w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin"></div>
        </div>

        <template v-for="(msg, idx) in messages" :key="msg.id">
          <!-- Separador de dia -->
          <div
            v-if="idx === 0 || isDifferentDay(messages[idx - 1].created_at, msg.created_at)"
            class="flex items-center gap-3 my-2"
          >
            <div class="flex-1 border-t border-white/5"></div>
            <span class="text-[10px] font-mono text-neutral-600 shrink-0">{{ formatDateSeparator(msg.created_at) }}</span>
            <div class="flex-1 border-t border-white/5"></div>
          </div>

          <div
          class="flex"
          :class="isOperator(msg.role) ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[70%] min-w-[60px]"
            :class="[isOperator(msg.role) ? 'items-end' : 'items-start', msg.scheduled_status === 'pending' ? 'opacity-60' : '']"
          >
            <!-- Role label -->
            <div
              class="flex items-center gap-1 mb-1 px-1"
              :class="isOperator(msg.role) ? 'justify-end' : 'justify-start'"
            >
              <Icon
                v-if="msg.role === 'assistant'"
                icon="solar:magic-stick-3-bold-duotone"
                class="text-[10px] text-accent/50"
              />
              <p
                class="text-[9px] font-mono uppercase tracking-widest"
                :class="isOperator(msg.role) ? 'text-accent/60' : msg.role === 'assistant' ? 'text-accent/50' : 'text-neutral-700'"
              >
                {{ roleLabel(msg.role, msg) }}
              </p>
            </div>

            <!-- Bubble -->
            <div
              class="px-4 py-2.5 text-sm leading-relaxed"
              :class="isOperator(msg.role)
                ? 'bg-accent/10 border border-accent/20 text-white'
                : msg.role === 'assistant'
                  ? 'bg-accent/[0.04] border border-accent/15 text-neutral-200'
                  : 'bg-surface border border-white/5 text-white'"
            >
              <!-- Attachments -->
              <div v-if="msg.attachments?.length" class="space-y-2 mb-1">
                <template v-for="att in msg.attachments" :key="att.id">
                  <!-- Imagem / GIF -->
                  <img
                    v-if="['image','gif'].includes(att.media_type)"
                    :src="att.file_url"
                    class="max-w-[240px] max-h-[240px] object-contain"
                  />
                  <!-- Sticker — com botão de salvar na biblioteca -->
                  <div
                    v-else-if="att.media_type === 'sticker'"
                    class="relative inline-block group"
                  >
                    <img
                      :src="att.file_url"
                      class="max-w-[160px] max-h-[160px] object-contain bg-transparent"
                    />
                    <button
                      v-if="!isOperator(msg.role)"
                      @click="saveSticker(att)"
                      class="absolute bottom-1 right-1 px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-widest border transition-all opacity-0 group-hover:opacity-100"
                      :class="savedAttachmentIds.has(att.id)
                        ? 'border-green-500/40 text-green-400 bg-canvas'
                        : 'border-white/20 text-neutral-400 bg-canvas hover:border-accent/50 hover:text-accent'"
                      :title="savedAttachmentIds.has(att.id) ? 'Salvo!' : 'Salvar na biblioteca'"
                    >
                      {{ savedAttachmentIds.has(att.id) ? 'Salvo' : '+ Salvar' }}
                    </button>
                  </div>
                  <!-- Vídeo -->
                  <video
                    v-else-if="att.media_type === 'video'"
                    :src="att.file_url"
                    controls
                    class="max-w-[240px] rounded-none"
                  ></video>
                  <!-- Áudio -->
                  <div v-else-if="['audio','ptt'].includes(att.media_type)" class="space-y-1.5">
                    <audio controls class="w-full max-w-[260px]" style="height:32px">
                      <source :src="att.file_url" type="audio/ogg" />
                      <source :src="att.file_url" type="audio/mpeg" />
                      <source :src="att.file_url" type="audio/mp4" />
                    </audio>
                    <p v-if="att.transcription_status === 'done' && att.transcription"
                      class="text-[11px] font-mono text-neutral-500 italic">
                      "{{ att.transcription }}"
                    </p>
                    <p v-else-if="att.transcription_status === 'pending'"
                      class="text-[10px] font-mono text-neutral-700">
                      Transcrevendo...
                    </p>
                  </div>
                  <!-- Documento -->
                  <a
                    v-else
                    :href="att.file_url"
                    target="_blank"
                    class="flex items-center gap-2 text-[11px] font-mono text-accent hover:underline"
                  >
                    <Icon icon="solar:file-bold-duotone" class="text-base shrink-0" />
                    Abrir arquivo
                  </a>
                </template>
              </div>

              <!-- Texto -->
              <span v-if="msg.content" class="whitespace-pre-wrap">{{ msg.content }}</span>
            </div>

            <!-- Timestamp / agendamento -->
            <div
              class="mt-1 px-1 flex items-center gap-1"
              :class="isOperator(msg.role) ? 'justify-end' : 'justify-start'"
            >
              <template v-if="msg.scheduled_status === 'pending'">
                <Icon icon="solar:clock-circle-bold-duotone" class="text-[10px] text-accent/50" />
                <p class="text-[9px] font-mono text-accent/50">
                  Agendada · {{ formatScheduled(msg.scheduled_at) }}
                </p>
              </template>
              <template v-else-if="msg.scheduled_status === 'failed'">
                <Icon icon="solar:close-circle-bold-duotone" class="text-[10px] text-red-500/60" />
                <p class="text-[9px] font-mono text-red-500/60">Falha no envio</p>
              </template>
              <p v-else class="text-[9px] font-mono text-neutral-700">
                {{ formatTime(msg.created_at) }}
              </p>
            </div>
          </div>
        </div>
        </template>

        <div ref="messagesEndRef"></div>
      </template>
    </div>

    <!-- Sticker picker -->
    <div v-if="showStickerPicker" class="border-t border-white/5 bg-surface p-4 shrink-0">
      <div class="flex items-center justify-between mb-3">
        <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500">Figurinhas</p>
        <button @click="showStickerPicker = false" class="text-neutral-400 hover:text-white transition-colors">
          <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
        </button>
      </div>
      <div v-if="stickers.length === 0" class="text-center py-4">
        <p class="text-xs font-mono text-neutral-700">Nenhuma figurinha salva.</p>
      </div>
      <div v-else class="grid grid-cols-6 gap-2 max-h-36 overflow-y-auto">
        <div
          v-for="sticker in stickers"
          :key="sticker.id"
          class="relative aspect-square group"
        >
          <button
            @click="sendSticker(sticker)"
            class="w-full h-full bg-canvas border border-white/5 hover:border-accent/30 transition-colors p-1"
          >
            <img :src="sticker.file_url" :alt="sticker.name" class="w-full h-full object-contain" />
          </button>
          <button
            @click.stop="deleteSticker(sticker)"
            class="absolute top-0.5 right-0.5 w-4 h-4 flex items-center justify-center bg-black/70 text-neutral-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
            title="Remover"
          >
            <Icon icon="solar:close-square-bold" class="text-[10px]" />
          </button>
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="border-t border-white/5 bg-surface shrink-0 relative">

      <!-- Scheduler -->
      <Transition name="scheduler">
        <div v-if="showScheduler" class="px-4 pt-3 pb-1 border-b border-white/5 flex items-center gap-3">
          <Icon icon="solar:calendar-bold-duotone" class="text-accent text-base shrink-0" />
          <input
            v-model="scheduledAt"
            type="datetime-local"
            :min="minDatetime"
            class="flex-1 bg-canvas border border-white/10 focus:border-accent/50 text-sm text-white font-mono px-3 py-1.5 outline-none"
          />
          <button
            v-if="scheduledAt"
            @click="scheduledAt = ''"
            class="text-[10px] font-mono text-neutral-300 hover:text-white transition-colors shrink-0"
          >
            Limpar
          </button>
          <button
            @click="showScheduler = false"
            class="text-neutral-400 hover:text-white transition-colors shrink-0"
          >
            <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
          </button>
        </div>
      </Transition>

      <!-- Template Picker -->
      <ConversationsTemplatePicker
        :templates="templates"
        :query="templateQuery"
        :visible="showTemplatePicker"
        @select-text="onTemplateSelectText"
        @select-media="onTemplateSelectMedia"
        @close="showTemplatePicker = false; text = ''"
      />

      <!-- Seletor de instância (só aparece com múltiplas instâncias) -->
      <div v-if="instances.length > 1" class="px-4 pt-2 pb-0 flex items-center gap-2 relative">
        <span class="text-[9px] font-mono text-neutral-700 uppercase tracking-widest">Enviar de</span>
        <div class="relative">
          <button
            @click="showInstanceSelector = !showInstanceSelector"
            class="flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-mono border transition-colors"
            :class="showInstanceSelector ? 'border-accent/30 text-accent' : 'border-white/10 text-neutral-400 hover:border-white/20 hover:text-neutral-200'"
          >
            <span
              class="w-1.5 h-1.5 rounded-full shrink-0"
              :class="selectedInstance?.status === 'connected' ? 'bg-green-400' : 'bg-neutral-600'"
            ></span>
            {{ selectedInstance?.phone_number || selectedInstance?.instance_name || 'Selecionar' }}
            <Icon icon="solar:alt-arrow-down-bold-duotone" class="text-[8px]" />
          </button>
          <div
            v-if="showInstanceSelector"
            class="absolute bottom-full left-0 mb-1 bg-surface border border-white/10 w-52 z-20 shadow-xl"
          >
            <button
              v-for="inst in instances"
              :key="inst.id"
              @click="selectedInstanceId = inst.id; showInstanceSelector = false"
              class="w-full flex items-center gap-2 px-3 py-2 text-xs font-mono transition-colors hover:bg-white/5"
              :class="selectedInstanceId === inst.id ? 'text-accent' : 'text-neutral-400'"
            >
              <span
                class="w-1.5 h-1.5 rounded-full shrink-0"
                :class="inst.status === 'connected' ? 'bg-green-400' : 'bg-neutral-600'"
              ></span>
              <span class="truncate">{{ inst.phone_number || inst.instance_name }}</span>
              <Icon v-if="selectedInstanceId === inst.id" icon="solar:check-circle-bold-duotone" class="text-accent ml-auto shrink-0" />
            </button>
          </div>
        </div>
      </div>

      <div class="flex items-end gap-2 px-4 py-3">

        <!-- Estado de gravação -->
        <template v-if="isRecording">
          <div class="flex-1 flex items-center gap-3 py-1.5">
            <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse shrink-0"></span>
            <span class="text-sm font-mono text-red-400">{{ formatRecordingTime(recordingSeconds) }}</span>
            <span class="text-[11px] font-mono text-neutral-600">Gravando... clique em enviar ou cancele</span>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <!-- Cancelar -->
            <button
              @click="cancelRecording"
              class="p-2 text-neutral-300 hover:text-red-400 transition-colors"
              title="Cancelar gravação"
            >
              <Icon icon="solar:close-circle-bold-duotone" class="text-lg" />
            </button>
            <!-- Enviar áudio -->
            <button
              @click="stopRecording"
              class="p-2 text-accent hover:text-orange-300 transition-colors"
              title="Enviar áudio"
            >
              <Icon icon="solar:plain-2-bold-duotone" class="text-lg" />
            </button>
          </div>
        </template>

        <!-- Estado normal -->
        <template v-else>
          <textarea
            v-model="text"
            @keydown="onKeydown"
            @input="onTextInput"
            :disabled="conv.status === 'closed'"
            placeholder="Digite uma mensagem... (/ para templates)"
            rows="1"
            class="flex-1 bg-transparent text-sm text-white placeholder-neutral-700 outline-none resize-none font-mono leading-relaxed py-1.5 disabled:opacity-40"
            style="max-height: 120px"
          ></textarea>

          <div class="flex items-center gap-1 shrink-0">
            <!-- Anexo -->
            <input
              ref="fileInputRef"
              type="file"
              class="hidden"
              @change="onFileChange"
              accept="image/*,audio/*,video/*,.pdf,.doc,.docx,.xls,.xlsx"
            />
            <button
              @click="fileInputRef?.click()"
              :disabled="conv.status === 'closed'"
              class="p-2 text-neutral-300 hover:text-white transition-colors disabled:opacity-40"
              title="Anexar arquivo"
            >
              <Icon icon="solar:paperclip-bold-duotone" class="text-lg" />
            </button>

            <!-- Figurinhas -->
            <button
              @click="openStickerPicker"
              :disabled="conv.status === 'closed'"
              class="p-2 transition-colors disabled:opacity-40"
              :class="showStickerPicker ? 'text-accent' : 'text-neutral-400 hover:text-neutral-300'"
              title="Figurinhas"
            >
              <Icon icon="solar:sticker-smile-circle-2-bold-duotone" class="text-lg" />
            </button>

            <!-- Agendar -->
            <button
              v-if="text.trim()"
              @click="showScheduler = !showScheduler"
              :disabled="conv.status === 'closed'"
              class="p-2 transition-colors disabled:opacity-40"
              :class="scheduledAt ? 'text-accent' : 'text-neutral-400 hover:text-neutral-300'"
              :title="scheduledAt ? `Agendado: ${formatScheduled(scheduledAt)}` : 'Agendar mensagem'"
            >
              <Icon icon="solar:calendar-bold-duotone" class="text-lg" />
            </button>

            <!-- Microfone (quando textarea vazio) ou Enviar (quando tem texto) -->
            <button
              v-if="!text.trim()"
              @click="startRecording"
              :disabled="conv.status === 'closed'"
              class="p-2 text-neutral-300 hover:text-white transition-colors disabled:opacity-40"
              title="Gravar áudio"
            >
              <Icon icon="solar:microphone-bold-duotone" class="text-lg" />
            </button>
            <button
              v-else
              @click="sendText"
              :disabled="sending || conv.status === 'closed'"
              class="p-2 transition-colors disabled:opacity-40"
              :class="scheduledAt ? 'text-accent' : 'text-accent hover:text-orange-300'"
              :title="scheduledAt ? 'Agendar' : 'Enviar'"
            >
              <Icon :icon="scheduledAt ? 'solar:clock-circle-bold-duotone' : 'solar:plain-2-bold-duotone'" class="text-lg" />
            </button>
          </div>
        </template>
      </div>

      <p v-if="conv.status === 'closed'" class="text-center text-[10px] font-mono text-neutral-700 pb-2">
        Conversa fechada — reabra para enviar mensagens
      </p>
    </div>

    <!-- Painel flutuante de anotações -->
    <Transition name="annotation-panel">
      <ConversationsAnnotationPanel
        v-if="showAnnotations"
        :contact-id="conv.contact.id"
        :contact-name="conv.contact.name"
        @close="showAnnotations = false"
        class="absolute inset-y-0 right-0 w-full sm:w-96 z-20"
      />
    </Transition>

    <!-- Painel flutuante Pipedrive -->
    <Transition name="annotation-panel">
      <ConversationsPipedrivePanel
        v-if="showPipedrive && conv.pipedrive_deal_id"
        :conversation-id="conv.id"
        :deal-id="conv.pipedrive_deal_id"
        @close="showPipedrive = false"
        class="absolute inset-y-0 right-0 w-full sm:w-96 z-20"
      />
    </Transition>
  </div>
</template>

<style scoped>
.scheduler-enter-active, .scheduler-leave-active { transition: opacity 0.15s, transform 0.15s }
.scheduler-enter-from, .scheduler-leave-to { opacity: 0; transform: translateY(4px) }

.annotation-panel-enter-active,
.annotation-panel-leave-active { transition: transform 0.2s ease, opacity 0.2s ease; }
.annotation-panel-enter-from,
.annotation-panel-leave-to     { transform: translateX(100%); opacity: 0; }
</style>
