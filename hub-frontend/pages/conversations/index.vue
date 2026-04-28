<script setup lang="ts">
import { Icon } from '@iconify/vue'

useHead({ title: 'Conversas' })

const api = useApi()
const { permission, requestPermission } = useNotifications()
const { has: hasUnread, total: totalUnread } = useUnread()
const { conversations, initFromRest, markAsRead } = useOrgWs()

const authStore = useAuthStore()
const loading = ref(true)
const selectedId = ref<number | null>(null)
const filter = ref<'open' | 'closed' | 'all' | 'mine'>('open')
const filterLabelId = ref<number | null>(null)
const newConvModal = ref(false)
const search = ref('')

const labelsStore = useLabelsStore()
onMounted(() => labelsStore.fetchLabels())

const filterInstanceId = ref<number | null>(null)
const instances = ref<any[]>([])
const showInstanceDrop = ref(false)
const showLabelDrop = ref(false)
const instanceDropRef = ref<HTMLElement>()
const labelDropRef = ref<HTMLElement>()

const filterAssignedToId = ref<number | null>(null)
const members = ref<any[]>([])
const showMemberDrop = ref(false)
const memberDropRef = ref<HTMLElement>()

const selectedInstanceLabel = computed(() => {
  if (!filterInstanceId.value) return 'Instância'
  const inst = instances.value.find((i: any) => i.id === filterInstanceId.value)
  return inst?.phone_number || inst?.instance_name || 'Instância'
})

const selectedLabelObj = computed(() =>
  filterLabelId.value ? labelsStore.labels.find((l: any) => l.id === filterLabelId.value) : null
)

const selectedMemberObj = computed(() =>
  filterAssignedToId.value ? members.value.find((m: any) => m.id === filterAssignedToId.value) : null
)

const closeDropdowns = (e: MouseEvent) => {
  if (instanceDropRef.value && !instanceDropRef.value.contains(e.target as Node)) showInstanceDrop.value = false
  if (labelDropRef.value && !labelDropRef.value.contains(e.target as Node)) showLabelDrop.value = false
  if (memberDropRef.value && !memberDropRef.value.contains(e.target as Node)) showMemberDrop.value = false
}
onMounted(() => document.addEventListener('click', closeDropdowns))
onUnmounted(() => document.removeEventListener('click', closeDropdowns))

const selectedConv = computed(() => conversations.value.find(c => c.id === selectedId.value) ?? null)

const filtered = computed(() => {
  let list: any[]
  if (filter.value === 'all') list = conversations.value
  else if (filter.value === 'mine') list = conversations.value.filter(c => c.assigned_to_id === authStore.user?.id)
  else list = conversations.value.filter(c => c.status === filter.value)
  if (filterLabelId.value) list = list.filter(c => c.labels?.some((l: any) => l.id === filterLabelId.value))
  if (filterInstanceId.value) list = list.filter(c => c.instance_id === filterInstanceId.value)
  if (filterAssignedToId.value) list = list.filter(c => c.assigned_to_id === filterAssignedToId.value)
  const q = search.value.trim().toLowerCase()
  if (!q) return list
  return list.filter(c =>
    c.contact.name?.toLowerCase().includes(q) ||
    c.contact.phone?.toLowerCase().includes(q) ||
    c.last_message?.content?.toLowerCase().includes(q)
  )
})

const visibleCount = ref(30)
const sentinelRef = ref<HTMLElement>()
const visibleConvs = computed(() => filtered.value.slice(0, visibleCount.value))
watch(filtered, () => { visibleCount.value = 30 })

// Atualiza o título da aba
watch(totalUnread, (count) => {
  if (!process.client) return
  document.title = count > 0 ? `(${count}) Hub` : 'Hub'
}, { immediate: true })

const fetchConversations = async () => {
  try {
    const data = await api<any[]>('/api/conversations/')
    initFromRest(data)
  } catch {}
  finally { loading.value = false }
}

let convObserver: IntersectionObserver | null = null
onMounted(async () => {
  await fetchConversations()
  try { instances.value = await api<any[]>('/api/integrations/whatsapp/') } catch {}
  try { members.value = await api<any[]>('/api/org/members') } catch {}
  if (process.client && 'Notification' in window && permission.value === 'default') {
    requestPermission()
  }
  convObserver = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting && visibleCount.value < filtered.value.length)
      visibleCount.value += 30
  }, { threshold: 0.1 })
  watch(sentinelRef, el => { if (el) convObserver?.observe(el) }, { immediate: true })
})
onUnmounted(() => convObserver?.disconnect())

const onConvUpdated = (updated: any) => {
  const idx = conversations.value.findIndex(c => c.id === updated.id)
  if (idx !== -1) conversations.value[idx] = updated
}

const onConvDeleted = (id: number) => {
  conversations.value = conversations.value.filter(c => c.id !== id)
  selectedId.value = null
  mobileView.value = 'list'
}

const mobileView = ref<'list' | 'chat'>('list')

const selectConv = (id: number) => {
  selectedId.value = id
  mobileView.value = 'chat'
  markAsRead(id)
}

const onConvCreated = (conv: any) => {
  const exists = conversations.value.some(c => c.id === conv.id)
  if (!exists) conversations.value.unshift(conv)
  selectedId.value = conv.id
  mobileView.value = 'chat'
  newConvModal.value = false
}

const formatTime = (dt: string) => {
  const d = new Date(dt)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return 'agora'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}
</script>

<template>
  <div class="flex overflow-hidden h-full">
    <!-- Left: lista de conversas -->
    <div
      class="border-r border-white/5 flex flex-col bg-canvas shrink-0 w-full md:w-72"
      :class="mobileView === 'list' ? 'flex' : 'hidden md:flex'"
    >
      <!-- Header -->
      <div class="px-5 pt-6 pb-3 border-b border-white/5">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div>
              <p class="field-label mb-0.5">Inbox</p>
              <h1 class="text-lg font-medium text-white tracking-tight">Conversas</h1>
            </div>
            <!-- Badge total não lidas -->
            <span
              v-if="totalUnread > 0"
              class="text-[9px] font-mono bg-accent text-white px-1.5 py-0.5 rounded-full leading-none"
            >
              {{ totalUnread > 99 ? '99+' : totalUnread }}
            </span>
          </div>
          <button
            @click="newConvModal = true"
            class="w-7 h-7 flex items-center justify-center border border-white/10 text-neutral-300 hover:border-accent/50 hover:text-accent transition-colors"
            title="Nova conversa"
          >
            <Icon icon="solar:add-circle-bold-duotone" class="text-base" />
          </button>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-white/5 px-5 p-1">
        <button
          v-for="[key, label] in [['open','Abertas'],['closed','Fechadas'],['all','Todas'],['mine','Meus']]"
          :key="key"
          @click="filter = key as any"
          class="pb-2.5 mr-5 text-[10px] font-mono uppercase tracking-widest transition-colors border-b-2 -mb-px"
          :class="filter === key ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
        >
          {{ label }}
        </button>
      </div>

      <!-- Filtros: instância + etiqueta -->
      <div
        v-if="instances.length > 1 || labelsStore.labels.length > 0 || members.length > 1"
        class="px-3 py-2 border-b border-white/5 flex items-center gap-2 flex-wrap"
      >
        <!-- Dropdown instância -->
        <div v-if="instances.length > 1" ref="instanceDropRef" class="relative">
          <button
            @click.stop="showInstanceDrop = !showInstanceDrop; showLabelDrop = false"
            class="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-mono border transition-colors"
            :class="filterInstanceId ? 'border-accent/30 text-accent bg-accent/5' : 'border-white/10 text-neutral-500 hover:border-white/20 hover:text-neutral-300'"
          >
            <Icon icon="solar:smartphone-2-bold-duotone" class="text-xs" />
            <span class="max-w-[80px] truncate">{{ selectedInstanceLabel }}</span>
            <Icon icon="solar:alt-arrow-down-bold-duotone" class="text-[8px]" />
          </button>
          <div
            v-if="showInstanceDrop"
            class="absolute top-full left-0 mt-1 bg-surface border border-white/10 z-30 w-52 shadow-xl"
          >
            <button
              @click="filterInstanceId = null; showInstanceDrop = false"
              class="w-full flex items-center px-3 py-2 text-[10px] font-mono transition-colors hover:bg-white/5"
              :class="!filterInstanceId ? 'text-accent' : 'text-neutral-400'"
            >
              <span class="flex-1 text-left">Todas as instâncias</span>
              <Icon v-if="!filterInstanceId" icon="solar:check-circle-bold-duotone" class="text-accent text-xs" />
            </button>
            <div class="border-t border-white/5"></div>
            <button
              v-for="inst in instances"
              :key="inst.id"
              @click="filterInstanceId = inst.id; showInstanceDrop = false"
              class="w-full flex items-center gap-2 px-3 py-2 text-[10px] font-mono transition-colors hover:bg-white/5"
              :class="filterInstanceId === inst.id ? 'text-accent' : 'text-neutral-400'"
            >
              <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="inst.status === 'connected' ? 'bg-green-400' : 'bg-neutral-600'"></span>
              <span class="flex-1 truncate text-left">{{ inst.phone_number || inst.instance_name }}</span>
              <Icon v-if="filterInstanceId === inst.id" icon="solar:check-circle-bold-duotone" class="text-accent text-xs shrink-0" />
            </button>
          </div>
        </div>

        <!-- Dropdown etiqueta -->
        <div v-if="labelsStore.labels.length > 0" ref="labelDropRef" class="relative">
          <button
            @click.stop="showLabelDrop = !showLabelDrop; showInstanceDrop = false"
            class="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-mono border transition-colors"
            :class="filterLabelId ? 'border-accent/30 text-accent bg-accent/5' : 'border-white/10 text-neutral-500 hover:border-white/20 hover:text-neutral-300'"
            :style="selectedLabelObj ? `border-color: ${selectedLabelObj.color}50; background: ${selectedLabelObj.color}10; color: ${selectedLabelObj.color}` : ''"
          >
            <Icon icon="solar:tag-bold-duotone" class="text-xs" />
            <span class="max-w-[80px] truncate">{{ selectedLabelObj?.name || 'Etiqueta' }}</span>
            <Icon icon="solar:alt-arrow-down-bold-duotone" class="text-[8px]" />
          </button>
          <div
            v-if="showLabelDrop"
            class="absolute top-full left-0 mt-1 bg-surface border border-white/10 z-30 w-48 shadow-xl max-h-60 overflow-y-auto"
          >
            <button
              @click="filterLabelId = null; showLabelDrop = false"
              class="w-full flex items-center px-3 py-2 text-[10px] font-mono transition-colors hover:bg-white/5"
              :class="!filterLabelId ? 'text-accent' : 'text-neutral-400'"
            >
              <span class="flex-1 text-left">Todas as etiquetas</span>
              <Icon v-if="!filterLabelId" icon="solar:check-circle-bold-duotone" class="text-accent text-xs" />
            </button>
            <div class="border-t border-white/5"></div>
            <button
              v-for="label in labelsStore.labels"
              :key="label.id"
              @click="filterLabelId = label.id; showLabelDrop = false"
              class="w-full flex items-center gap-2 px-3 py-2 text-[10px] font-mono transition-colors hover:bg-white/5"
              :class="filterLabelId === label.id ? 'text-white' : 'text-neutral-400'"
            >
              <span class="w-2 h-2 rounded-full shrink-0" :style="`background: ${label.color}`"></span>
              <span class="flex-1 truncate text-left">{{ label.name }}</span>
              <Icon v-if="filterLabelId === label.id" icon="solar:check-circle-bold-duotone" class="text-xs shrink-0" :style="`color: ${label.color}`" />
            </button>
          </div>
        </div>

        <!-- Dropdown responsável -->
        <div v-if="members.length > 1" ref="memberDropRef" class="relative">
          <button
            @click.stop="showMemberDrop = !showMemberDrop; showInstanceDrop = false; showLabelDrop = false"
            class="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-mono border transition-colors"
            :class="filterAssignedToId ? 'border-accent/30 text-accent bg-accent/5' : 'border-white/10 text-neutral-500 hover:border-white/20 hover:text-neutral-300'"
          >
            <Icon icon="solar:user-bold-duotone" class="text-xs" />
            <span class="max-w-[80px] truncate">{{ selectedMemberObj?.name?.split(' ')[0] || 'Responsável' }}</span>
            <Icon icon="solar:alt-arrow-down-bold-duotone" class="text-[8px]" />
          </button>
          <div
            v-if="showMemberDrop"
            class="absolute top-full left-0 mt-1 bg-surface border border-white/10 z-30 w-48 shadow-xl max-h-60 overflow-y-auto"
          >
            <button
              @click="filterAssignedToId = null; showMemberDrop = false"
              class="w-full flex items-center px-3 py-2 text-[10px] font-mono transition-colors hover:bg-white/5"
              :class="!filterAssignedToId ? 'text-accent' : 'text-neutral-400'"
            >
              <span class="flex-1 text-left">Todos os responsáveis</span>
              <Icon v-if="!filterAssignedToId" icon="solar:check-circle-bold-duotone" class="text-accent text-xs" />
            </button>
            <div class="border-t border-white/5"></div>
            <button
              v-for="member in members"
              :key="member.id"
              @click="filterAssignedToId = member.id; showMemberDrop = false"
              class="w-full flex items-center gap-2 px-3 py-2 text-[10px] font-mono transition-colors hover:bg-white/5"
              :class="filterAssignedToId === member.id ? 'text-accent' : 'text-neutral-400'"
            >
              <span class="flex-1 truncate text-left">{{ member.name || member.email }}</span>
              <Icon v-if="filterAssignedToId === member.id" icon="solar:check-circle-bold-duotone" class="text-accent text-xs shrink-0" />
            </button>
          </div>
        </div>
      </div>

      <!-- Busca -->
      <div class="px-3 py-2 border-b border-white/5">
        <div class="flex items-center gap-2 px-3 py-1.5 bg-canvas border border-white/5 focus-within:border-accent/30 transition-colors">
          <Icon icon="solar:magnifer-bold-duotone" class="text-sm text-neutral-600 shrink-0" />
          <input
            v-model="search"
            type="text"
            placeholder="Buscar conversa..."
            class="bg-transparent text-xs font-mono text-white outline-none placeholder-neutral-700 flex-1 min-w-0"
          />
          <button v-if="search" @click="search = ''" class="text-neutral-600 hover:text-neutral-400 transition-colors">
            <Icon icon="solar:close-circle-bold-duotone" class="text-sm" />
          </button>
        </div>
      </div>

      <!-- Lista -->
      <div class="flex-1 overflow-y-auto scrollbar-thin">
        <div v-if="loading" class="space-y-px pt-1">
          <div v-for="i in 6" :key="i" class="px-5 py-4 animate-pulse">
            <div class="h-3 bg-white/5 rounded w-28 mb-2"></div>
            <div class="h-2 bg-white/5 rounded w-40"></div>
          </div>
        </div>

        <div v-else-if="filtered.length === 0" class="flex flex-col items-center justify-center h-48 text-center px-6">
          <Icon icon="solar:chat-round-dots-bold-duotone" class="text-4xl text-white/10 mb-3" />
          <p class="text-xs font-mono text-neutral-700">{{ search ? 'Nenhum resultado' : 'Nenhuma conversa' }}</p>
        </div>

        <template v-else>
          <button
            v-for="conv in visibleConvs"
            :key="conv.id"
            @click="selectConv(conv.id)"
            class="w-full px-5 py-3.5 text-left border-b border-white/5 transition-colors hover:bg-white/[0.02] relative"
            :class="selectedId === conv.id ? 'bg-white/[0.04]' : ''"
          >
            <div
              v-if="selectedId === conv.id"
              class="absolute left-0 top-0 bottom-0 w-0.5 bg-accent"
            ></div>
            <div class="flex items-start justify-between gap-2">
              <div class="flex items-center gap-2.5 min-w-0">
                <div class="relative shrink-0">
                  <div
                    class="w-1.5 h-1.5 rounded-full"
                    :class="conv.status === 'open' ? 'bg-green-400' : 'bg-neutral-700'"
                  ></div>
                  <!-- Ponto de não lida -->
                  <div
                    v-if="hasUnread(conv.id)"
                    class="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-accent"
                  ></div>
                </div>
                <div class="min-w-0">
                  <p
                    class="text-sm font-medium truncate"
                    :class="hasUnread(conv.id) ? 'text-white' : 'text-white'"
                  >{{ conv.contact.name }}</p>
                  <!-- Preview da última mensagem -->
                  <p
                    v-if="conv.last_message"
                    class="text-[11px] font-mono truncate mt-0.5"
                    :class="hasUnread(conv.id) ? 'text-neutral-400' : 'text-neutral-600'"
                  >
                    <span v-if="conv.last_message.role === 'operator'" class="text-neutral-700">Você: </span>
                    <span v-else-if="conv.last_message.role === 'assistant'" class="text-neutral-700">IA: </span>
                    {{ conv.last_message.content || '📎 Arquivo' }}
                  </p>
                  <p v-else class="text-[11px] font-mono text-neutral-600 truncate">{{ conv.contact.phone }}</p>
                  <div v-if="conv.labels?.length" class="flex flex-wrap gap-1 mt-1">
                    <LabelsLabelBadge
                      v-for="l in conv.labels.slice(0, 2)"
                      :key="l.id"
                      :name="l.name"
                      :color="l.color"
                    />
                    <span v-if="conv.labels.length > 2" class="text-[9px] font-mono text-neutral-700">+{{ conv.labels.length - 2 }}</span>
                  </div>
                </div>
              </div>
              <div class="shrink-0 text-right flex flex-col items-end gap-1">
                <p class="text-[10px] font-mono" :class="hasUnread(conv.id) ? 'text-accent' : 'text-neutral-700'">
                  {{ conv.last_message ? formatTime(conv.last_message.created_at) : formatTime(conv.started_at) }}
                </p>
                <span v-if="conv.ai_active && conv.agent_id" class="text-[9px] font-mono text-accent bg-accent/10 px-1.5 py-0.5 uppercase tracking-widest">IA</span>
                <span
                  v-if="instances.length > 1 && conv.instance_name"
                  class="text-[9px] font-mono text-neutral-600 bg-white/5 px-1.5 py-0.5 uppercase tracking-widest max-w-[60px] truncate"
                  :title="conv.instance_name"
                >{{ conv.instance_name }}</span>
                <span
                  v-if="conv.assigned_to_name"
                  class="text-[9px] font-mono text-neutral-500 bg-white/5 px-1.5 py-0.5 uppercase tracking-widest max-w-[60px] truncate"
                  :title="conv.assigned_to_name"
                >{{ conv.assigned_to_name.split(' ')[0] }}</span>
              </div>
            </div>
          </button>
          <div v-if="visibleCount < filtered.length" ref="sentinelRef" class="h-4"></div>
        </template>
      </div>
    </div>

    <!-- Right: chat -->
    <div
      class="flex-1 overflow-hidden"
      :class="mobileView === 'chat' ? 'block' : 'hidden md:block'"
    >
      <ConversationsChat
        v-if="selectedConv"
        :key="selectedConv.id"
        :conversation="selectedConv"
        :show-back="true"
        @updated="onConvUpdated"
        @deleted="onConvDeleted"
        @back="mobileView = 'list'"
      />
      <div v-else class="h-full flex flex-col items-center justify-center text-center">
        <Icon icon="solar:chat-round-dots-bold-duotone" class="text-6xl text-white/5 mb-4" />
        <p class="text-sm font-mono text-neutral-700">Selecione uma conversa</p>
      </div>
    </div>
  </div>

  <ConversationsNewConversationModal
    :open="newConvModal"
    :active-conversations="conversations"
    @close="newConvModal = false"
    @created="onConvCreated"
  />
</template>
