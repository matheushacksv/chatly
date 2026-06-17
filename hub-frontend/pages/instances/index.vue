<script setup lang="ts">
import { Icon } from '@iconify/vue'

useHead({ title: 'Instâncias' })

const api = useApi()
const authStore = useAuthStore()

const instances = ref<any[]>([])
const agents = ref<any[]>([])
const loading = ref(true)
const subscription = ref<any>(null)

const isOwnerOrAdmin = computed(() => ['owner', 'admin'].includes(authStore.user?.role ?? ''))
const instanceLimit = computed(() => subscription.value?.max_instances_total ?? null)
const instancesUsed = computed(() => subscription.value?.usage?.instances_used ?? instances.value.length)
const atLimit = computed(() => instanceLimit.value !== null && instancesUsed.value >= instanceLimit.value)

const createModal = ref(false)
const connectModal = ref(false)
const selectedInstance = ref<any>(null)

// ---- Trocar agente ----
const editAgentInstance = ref<any>(null)
const editAgentId = ref<number | null>(null)
const editAgentLoading = ref(false)

// ---- Fila de atendimento ----
const queueInstance = ref<any>(null)
const showQueueModal = ref(false)
const openQueue = (instance: any) => {
  queueInstance.value = instance
  showQueueModal.value = true
}

// ---- Atualizar status ----
const refreshingId = ref<number | null>(null)

const fetchInstances = async () => {
  loading.value = true
  try {
    ;[instances.value, agents.value] = await Promise.all([
      api<any[]>('/api/integrations/whatsapp/'),
      api<any[]>('/api/agents/'),
    ])
  } catch {}
  finally { loading.value = false }
}

onMounted(async () => {
  await fetchInstances()
  try { subscription.value = await api<any>('/api/billing/') } catch {}
})

const { page: instPage, totalPages: instTotalPages, paged: pagedInstances, prev: instPrev, next: instNext, goTo: instGoTo } = usePagination(instances, 10)

const agentName = (agentId: number | null) => {
  if (!agentId) return null
  return agents.value.find(a => a.id === agentId)?.name ?? `#${agentId}`
}

const openConnect = (instance: any) => {
  selectedInstance.value = instance
  connectModal.value = true
}

const onCreated = (instance: any) => {
  instances.value.push(instance)
  createModal.value = false
}

const onConnected = async () => {
  connectModal.value = false
  await fetchInstances()
}

const logout = async (instance: any) => {
  try {
    await api(`/api/integrations/whatsapp/${instance.id}/logout`, { method: 'DELETE' })
    await fetchInstances()
  } catch (e: any) {
    alert(e?.data?.detail || 'Erro ao desconectar')
  }
}

const { confirm: confirmDialog } = useConfirm()

const deleteInstance = async (instance: any) => {
  const ok = await confirmDialog(`Deletar a instância "${instance.instance_name}"? Esta ação é irreversível.`, { title: 'Deletar instância' })
  if (!ok) return
  try {
    await api(`/api/integrations/whatsapp/${instance.id}`, { method: 'DELETE' })
    instances.value = instances.value.filter((i) => i.id !== instance.id)
  } catch (e: any) {
    alert(e?.data?.detail || 'Erro ao deletar instância')
  }
}

// ---- Atualizar status ----
const refreshStatus = async (instance: any) => {
  refreshingId.value = instance.id
  try {
    const updated = await api<any>(`/api/integrations/whatsapp/${instance.id}/status`)
    const idx = instances.value.findIndex(i => i.id === instance.id)
    if (idx !== -1) instances.value[idx] = { ...instances.value[idx], ...updated }
  } catch {}
  finally { refreshingId.value = null }
}

// ---- Trocar agente ----
const openEditAgent = (instance: any) => {
  editAgentInstance.value = instance
  editAgentId.value = instance.agent_id ?? null
}

const saveAgent = async () => {
  if (!editAgentInstance.value) return
  editAgentLoading.value = true
  try {
    const url = editAgentId.value
      ? `/api/integrations/whatsapp/${editAgentInstance.value.id}/agent?agent_id=${editAgentId.value}`
      : `/api/integrations/whatsapp/${editAgentInstance.value.id}/agent`
    const updated = await api<any>(url, { method: 'PATCH' })
    const idx = instances.value.findIndex(i => i.id === updated.id)
    if (idx !== -1) instances.value[idx] = { ...instances.value[idx], ...updated }
    editAgentInstance.value = null
  } catch (e: any) {
    alert(e?.data?.detail || 'Erro ao atualizar agente')
  } finally {
    editAgentLoading.value = false
  }
}

const statusColor = (status: string) => ({
  'bg-green-400': status === 'connected',
  'bg-yellow-400': status === 'connecting',
  'bg-red-500': status === 'disconnected',
})

const statusLabel = (status: string) => ({
  connected: 'Conectado',
  connecting: 'Conectando',
  disconnected: 'Desconectado',
}[status] ?? status)
</script>

<template>
  <div class="p-4 md:p-8 max-w-4xl">
    <!-- Header -->
    <div class="flex flex-wrap items-start justify-between gap-y-3 mb-10">
      <div>
        <p class="field-label mb-1">WhatsApp</p>
        <h1 class="text-2xl font-medium text-white tracking-tight">Instâncias</h1>
        <p v-if="instanceLimit !== null" class="text-[10px] font-mono mt-1" :class="atLimit ? 'text-red-500' : 'text-neutral-600'">
          {{ instancesUsed }}/{{ instanceLimit }} instâncias
          <NuxtLink v-if="atLimit" to="/billing" class="text-accent hover:underline ml-1">fazer upgrade</NuxtLink>
        </p>
      </div>
      <button v-if="isOwnerOrAdmin" @click="createModal = true" :disabled="atLimit" class="btn-primary !w-auto px-5 py-3 disabled:opacity-40 disabled:cursor-not-allowed">
        <div class="corner-tl"></div>
        <div class="corner-br"></div>
        <span class="text-white text-xs font-mono uppercase tracking-wider flex items-center gap-2">
          <Icon icon="solar:add-circle-bold-duotone" class="text-sm" />
          Nova instância
        </span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="bg-surface border border-white/5 p-6 animate-pulse">
        <div class="flex items-center gap-4">
          <div class="w-2 h-2 rounded-full bg-white/5"></div>
          <div class="h-3 bg-white/5 rounded w-32"></div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="instances.length === 0"
      class="bg-surface border border-white/5 p-12 flex flex-col items-center justify-center text-center"
    >
      <Icon icon="solar:smartphone-2-bold-duotone" class="text-5xl text-white/10 mb-4" />
      <p class="text-sm text-neutral-500 mb-1">Nenhuma instância configurada</p>
      <p class="text-xs font-mono text-neutral-700 mb-6">Crie uma instância para começar a receber mensagens</p>
      <button v-if="isOwnerOrAdmin" @click="createModal = true" class="btn-primary !w-auto px-6 py-3">
        <div class="corner-tl"></div>
        <div class="corner-br"></div>
        <span class="text-white text-xs font-mono uppercase tracking-wider">Criar primeira instância</span>
      </button>
    </div>

    <!-- Instances list -->
    <div v-else class="space-y-3">
      <div
        v-for="instance in pagedInstances"
        :key="instance.id"
        class="bg-surface border border-white/5 hover:border-white/10 transition-colors"
      >
        <!-- Main row -->
        <div class="p-5 flex flex-wrap items-center justify-between gap-y-3">
          <!-- Info -->
          <div class="flex items-center gap-4">
            <div class="w-2 h-2 rounded-full shrink-0" :class="statusColor(instance.status)"></div>
            <div>
              <p class="text-sm text-white font-medium">{{ instance.instance_name }}</p>
              <div class="flex items-center gap-3 mt-0.5">
                <span
                  class="text-[10px] font-mono uppercase tracking-widest"
                  :class="{
                    'text-green-400': instance.status === 'connected',
                    'text-yellow-400': instance.status === 'connecting',
                    'text-red-500': instance.status === 'disconnected',
                  }"
                >{{ statusLabel(instance.status) }}</span>
                <span
                  v-if="instance.needs_qr"
                  class="text-[10px] font-mono uppercase tracking-widest text-amber-400 border border-amber-500/40 px-1.5 py-0.5"
                  title="Sessão desautenticada — reconecte escaneando o QR"
                >Escanear QR</span>
                <span v-if="instance.phone_number" class="text-[10px] font-mono text-neutral-600">
                  {{ instance.phone_number }}
                </span>
                <span v-if="agentName(instance.agent_id)" class="text-[10px] font-mono text-neutral-500">
                  · {{ agentName(instance.agent_id) }}
                </span>
                <span v-else class="text-[10px] font-mono text-neutral-700">· Sem agente</span>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1">
            <!-- Atualizar status -->
            <button
              @click="refreshStatus(instance)"
              class="p-2 text-neutral-300 hover:text-white transition-colors"
              :class="{ 'animate-spin': refreshingId === instance.id }"
              title="Atualizar status"
            >
              <Icon icon="solar:refresh-bold-duotone" class="text-base" />
            </button>

            <!-- Trocar agente (owner/admin) -->
            <button
              v-if="isOwnerOrAdmin"
              @click="openEditAgent(instance)"
              class="p-2 text-neutral-300 hover:text-white transition-colors"
              title="Trocar agente"
            >
              <Icon icon="solar:cpu-bolt-bold-duotone" class="text-base" />
            </button>

            <!-- Fila de atendimento (owner/admin) -->
            <button
              v-if="isOwnerOrAdmin"
              @click="openQueue(instance)"
              class="p-2 text-neutral-300 hover:text-white transition-colors"
              title="Fila de atendimento"
            >
              <Icon icon="solar:users-group-rounded-bold-duotone" class="text-base" />
            </button>

            <!-- Conectar / Desconectar (owner/admin) -->
            <template v-if="isOwnerOrAdmin">
              <button
                v-if="instance.status !== 'connected'"
                @click="openConnect(instance)"
                class="px-3 sm:px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-neutral-800 text-neutral-400 hover:border-accent hover:text-accent transition-colors"
              >
                Conectar
              </button>
              <button
                v-else
                @click="logout(instance)"
                class="px-3 sm:px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-neutral-800 text-neutral-400 hover:border-yellow-500 hover:text-yellow-500 transition-colors"
              >
                Desconectar
              </button>
            </template>

            <!-- Deletar (owner/admin) -->
            <button
              v-if="isOwnerOrAdmin"
              @click="deleteInstance(instance)"
              class="p-2 text-neutral-300 hover:text-red-500 transition-colors"
              title="Deletar instância"
            >
              <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-base" />
            </button>
          </div>
        </div>

        <!-- Inline: editar agente -->
        <div
          v-if="editAgentInstance?.id === instance.id"
          class="border-t border-white/5 px-5 py-4 flex items-center gap-3 bg-canvas"
        >
          <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-600 shrink-0">Agente</p>
          <select
            v-model="editAgentId"
            class="flex-1 bg-surface border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
          >
            <option :value="null">Sem agente</option>
            <option v-for="a in agents" :key="a.id" :value="a.id">{{ a.name }}</option>
          </select>
          <button
            @click="saveAgent"
            :disabled="editAgentLoading"
            class="px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-accent/30 text-accent hover:bg-accent/5 transition-colors disabled:opacity-50"
          >
            {{ editAgentLoading ? 'Salvando...' : 'Salvar' }}
          </button>
          <button
            @click="editAgentInstance = null"
            class="p-2 text-neutral-300 hover:text-white transition-colors"
          >
            <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
          </button>
        </div>
      </div>
    </div>

    <AppPagination
      v-if="instTotalPages > 1"
      :page="instPage"
      :total-pages="instTotalPages"
      @prev="instPrev"
      @next="instNext"
      @go-to="instGoTo"
    />
  </div>

  <!-- Modals -->
  <InstancesCreateInstanceModal
    :open="createModal"
    @close="createModal = false"
    @created="onCreated"
  />
  <InstancesConnectModal
    :open="connectModal"
    :instance="selectedInstance"
    @close="connectModal = false"
    @connected="onConnected"
  />
  <InstancesQueueModal
    v-if="showQueueModal"
    :instance="queueInstance"
    @close="showQueueModal = false"
  />
</template>
