<script setup lang="ts">
import { Icon } from '@iconify/vue'

useHead({ title: 'Agentes' })

const api = useApi()
const authStore = useAuthStore()
const { confirm: confirmDialog } = useConfirm()

const providers = ref<any[]>([])
const agents = ref<any[]>([])
const orgMembers = ref<any[]>([])
const loading = ref(true)

const isOwnerOrAdmin = computed(() => ['owner', 'admin'].includes(authStore.user?.role ?? ''))
const canView = computed(() => isOwnerOrAdmin.value || (authStore.user?.permissions?.can_view_agents ?? false))
const canCreate = computed(() => isOwnerOrAdmin.value || (authStore.user?.permissions?.can_create_agents ?? false))
const canEdit = computed(() => isOwnerOrAdmin.value || (authStore.user?.permissions?.can_edit_agents ?? false))
const canDelete = computed(() => isOwnerOrAdmin.value || (authStore.user?.permissions?.can_delete_agents ?? false))
const hasAnyAgentPermission = computed(() => canView.value || canCreate.value || canEdit.value || canDelete.value)

const addProviderModal = ref(false)
const selectedProviderType = ref('')
const agentModal = ref(false)
const editingAgent = ref<any>(null)

// ---- Membros do agente ----
const membersModal = ref(false)
const membersAgent = ref<any>(null)
const memberships = ref<any[]>([])
const membersLoading = ref(false)
const addMemberId = ref<number | null>(null)
const addMemberLoading = ref(false)

const PROVIDER_TYPES = [
  { type: 'openai', label: 'OpenAI', icon: 'simple-icons:openai', description: 'GPT-4o, GPT-4 Turbo e mais' },
  { type: 'anthropic', label: 'Anthropic', icon: 'simple-icons:anthropic', description: 'Claude Opus, Sonnet e Haiku' },
  { type: 'groq', label: 'Groq', icon: 'simple-icons:groq', description: 'Llama, Mixtral — inferência rápida' },
]

const fetchAll = async () => {
  loading.value = true
  try {
    ;[providers.value, agents.value, orgMembers.value] = await Promise.all([
      api<any[]>('/api/agents/providers'),
      api<any[]>('/api/agents/'),
      api<any[]>('/api/org/members'),
    ])
  } catch {}
  finally { loading.value = false }
}

onMounted(fetchAll)

const isProviderConfigured = (type: string) => providers.value.some(p => p.provider_type === type)
const getProvider = (type: string) => providers.value.find(p => p.provider_type === type)

const openAddProvider = (type: string) => {
  selectedProviderType.value = type
  addProviderModal.value = true
}

const removeProvider = async (type: string) => {
  const p = getProvider(type)
  if (!p) return
  if (!await confirmDialog(`Remover provedor ${type}? Agentes que usam esse provedor serão afetados.`, { title: 'Remover provedor' })) return
  try {
    await api(`/api/agents/providers/${p.id}`, { method: 'DELETE' })
    providers.value = providers.value.filter((x: any) => x.id !== p.id)
  } catch (e: any) {
    alert(e?.data?.detail || 'Erro ao remover provedor')
  }
}

const openCreateAgent = () => {
  editingAgent.value = null
  agentModal.value = true
}

const openEditAgent = (agent: any) => {
  editingAgent.value = agent
  agentModal.value = true
}

const deleteAgent = async (agent: any) => {
  if (!await confirmDialog(`Deletar o agente "${agent.name}"?`, { title: 'Deletar agente' })) return
  try {
    await api(`/api/agents/${agent.id}`, { method: 'DELETE' })
    agents.value = agents.value.filter((a: any) => a.id !== agent.id)
  } catch (e: any) {
    alert(e?.data?.detail || 'Erro ao deletar agente')
  }
}

const onProviderAdded = (provider: any) => {
  providers.value.push(provider)
  addProviderModal.value = false
}

const onAgentSaved = (agent: any, isEdit: boolean) => {
  if (isEdit) {
    const idx = agents.value.findIndex((a: any) => a.id === agent.id)
    if (idx !== -1) agents.value[idx] = agent
  } else {
    agents.value.push(agent)
  }
  agentModal.value = false
}

const providerLabel = (type: string) => PROVIDER_TYPES.find(p => p.type === type)?.label ?? type

const { page: agPage, totalPages: agTotalPages, paged: pagedAgents, prev: agPrev, next: agNext, goTo: agGoTo } = usePagination(agents, 10)

// ---- Membros do agente ----
const openMembersModal = async (agent: any) => {
  membersAgent.value = agent
  membersModal.value = true
  memberships.value = []
  addMemberId.value = null
  membersLoading.value = true
  try {
    memberships.value = await api<any[]>(`/api/agents/${agent.id}/members`)
  } catch {}
  finally { membersLoading.value = false }
}

const memberName = (userId: number) => {
  const m = orgMembers.value.find(m => m.id === userId)
  return m ? (m.name || m.email) : `#${userId}`
}

const memberEmail = (userId: number) => {
  return orgMembers.value.find(m => m.id === userId)?.email ?? ''
}

// Membros da org que ainda não estão no agente
const availableMembers = computed(() => {
  const assignedIds = new Set(memberships.value.map(m => m.user_id))
  return orgMembers.value.filter(m => !assignedIds.has(m.id))
})

const addMember = async () => {
  if (!addMemberId.value || !membersAgent.value) return
  addMemberLoading.value = true
  try {
    const membership = await api<any>(`/api/agents/${membersAgent.value.id}/members`, {
      method: 'POST',
      body: { user_id: addMemberId.value },
    })
    memberships.value.push(membership)
    addMemberId.value = null
  } catch (e: any) {
    alert(e?.data?.detail || 'Erro ao adicionar membro')
  } finally {
    addMemberLoading.value = false
  }
}

const removeMember = async (membership: any) => {
  try {
    await api(`/api/agents/${membersAgent.value.id}/members/${membership.user_id}`, { method: 'DELETE' })
    memberships.value = memberships.value.filter(m => m.id !== membership.id)
  } catch (e: any) {
    alert(e?.data?.detail || 'Erro ao remover membro')
  }
}
</script>

<template>
  <div class="p-4 md:p-8 max-w-4xl">
    <!-- Header -->
    <div class="mb-10">
      <p class="field-label mb-1">IA</p>
      <h1 class="text-2xl font-medium text-white tracking-tight">Agentes</h1>
    </div>

    <!-- Sem permissão -->
    <div v-if="!loading && !hasAnyAgentPermission" class="flex items-center gap-3 p-5 border border-white/5 bg-surface text-xs font-mono text-neutral-500">
      <Icon icon="solar:lock-bold-duotone" class="text-base shrink-0" />
      Você não tem permissão para gerenciar agentes. Contate um administrador.
    </div>

    <!-- Skeleton -->
    <div v-else-if="loading" class="space-y-3">
      <div v-for="i in 4" :key="i" class="bg-surface border border-white/5 p-6 animate-pulse">
        <div class="h-3 bg-white/5 rounded w-40 mb-2"></div>
        <div class="h-2.5 bg-white/5 rounded w-64"></div>
      </div>
    </div>

    <template v-else>
      <!-- Provedores -->
      <div class="mb-10">
        <p class="field-label mb-4">Provedores de IA</p>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div
            v-for="pt in PROVIDER_TYPES"
            :key="pt.type"
            class="bg-surface border p-5 transition-colors"
            :class="isProviderConfigured(pt.type) ? 'border-white/10' : 'border-white/5'"
          >
            <div class="flex items-start justify-between mb-3">
              <Icon
                :icon="pt.icon"
                class="text-xl"
                :class="isProviderConfigured(pt.type) ? 'text-white' : 'text-white/20'"
              />
              <span
                class="text-[9px] font-mono uppercase tracking-widest px-2 py-0.5"
                :class="isProviderConfigured(pt.type) ? 'text-green-400 bg-green-400/10' : 'text-neutral-600 bg-white/5'"
              >
                {{ isProviderConfigured(pt.type) ? 'Ativo' : 'Inativo' }}
              </span>
            </div>
            <p class="text-sm font-medium text-white mb-0.5">{{ pt.label }}</p>
            <p class="text-[11px] font-mono text-neutral-600 mb-4">{{ pt.description }}</p>
            <template v-if="isOwnerOrAdmin">
              <button
                v-if="!isProviderConfigured(pt.type)"
                @click="openAddProvider(pt.type)"
                class="text-[10px] font-mono uppercase tracking-widest text-accent hover:text-orange-300 transition-colors"
              >
                Configurar →
              </button>
              <button
                v-else
                @click="removeProvider(pt.type)"
                class="text-[10px] font-mono uppercase tracking-widest text-neutral-400 hover:text-red-500 transition-colors"
              >
                Remover
              </button>
            </template>
          </div>
        </div>
      </div>

      <!-- Agentes -->
      <div>
        <div class="flex flex-wrap items-center justify-between gap-y-3 mb-4">
          <p class="field-label">Agentes configurados</p>
          <button v-if="canCreate" @click="openCreateAgent" class="btn-primary !w-auto px-5 py-2.5">
            <div class="corner-tl"></div>
            <div class="corner-br"></div>
            <span class="text-white text-xs font-mono uppercase tracking-wider flex items-center gap-2">
              <Icon icon="solar:add-circle-bold-duotone" class="text-sm" />
              Novo agente
            </span>
          </button>
        </div>

        <!-- Empty state -->
        <div
          v-if="agents.length === 0"
          class="bg-surface border border-white/5 p-12 flex flex-col items-center text-center"
        >
          <Icon icon="solar:cpu-bolt-bold-duotone" class="text-5xl text-white/10 mb-4" />
          <p class="text-sm text-neutral-500 mb-1">Nenhum agente configurado</p>
          <p class="text-xs font-mono text-neutral-700 mb-6">Crie um agente para automatizar o atendimento</p>
          <button v-if="canCreate" @click="openCreateAgent" class="btn-primary !w-auto px-6 py-3">
            <div class="corner-tl"></div>
            <div class="corner-br"></div>
            <span class="text-white text-xs font-mono uppercase tracking-wider">Criar agente</span>
          </button>
        </div>

        <!-- Agents list -->
        <div v-else class="space-y-3">
          <div
            v-for="agent in pagedAgents"
            :key="agent.id"
            class="bg-surface border border-white/5 p-5 flex flex-wrap items-center justify-between gap-y-3 hover:border-white/10 transition-colors"
          >
            <div class="flex items-center gap-4">
              <div
                class="w-2 h-2 rounded-full shrink-0"
                :class="agent.is_active ? 'bg-green-400' : 'bg-neutral-700'"
              ></div>
              <div>
                <p class="text-sm text-white font-medium">{{ agent.name }}</p>
                <div class="flex items-center gap-3 mt-0.5">
                  <span class="text-[10px] font-mono uppercase tracking-widest text-accent">
                    {{ providerLabel(agent.provider.provider_type) }}
                  </span>
                  <span class="text-[10px] font-mono text-neutral-600">{{ agent.model_name }}</span>
                  <span v-if="agent.description" class="text-[10px] font-mono text-neutral-700 truncate max-w-xs">
                    {{ agent.description }}
                  </span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <button
                v-if="isOwnerOrAdmin"
                @click="openMembersModal(agent)"
                class="px-2 sm:px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-neutral-800 text-neutral-400 hover:border-white/20 hover:text-white transition-colors"
                title="Gerenciar membros"
              >
                <Icon icon="solar:users-group-rounded-bold-duotone" class="text-sm inline sm:mr-1.5" />
                <span class="hidden sm:inline">Membros</span>
              </button>
              <button
                v-if="canEdit"
                @click="openEditAgent(agent)"
                class="px-2 sm:px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-neutral-800 text-neutral-400 hover:border-white/20 hover:text-white transition-colors"
                title="Editar agente"
              >
                <Icon icon="solar:pen-bold-duotone" class="text-sm inline sm:mr-1.5" />
                <span class="hidden sm:inline">Editar</span>
              </button>
              <button
                v-if="canDelete"
                @click="deleteAgent(agent)"
                class="p-2 text-neutral-300 hover:text-red-500 transition-colors"
                title="Deletar agente"
              >
                <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-base" />
              </button>
            </div>
          </div>
        </div>

        <AppPagination
          v-if="agTotalPages > 1"
          :page="agPage"
          :total-pages="agTotalPages"
          @prev="agPrev"
          @next="agNext"
          @go-to="agGoTo"
        />
      </div>
    </template>
  </div>

  <!-- Modal Provedores -->
  <AgentsAddProviderModal
    :open="addProviderModal"
    :provider-type="selectedProviderType"
    @close="addProviderModal = false"
    @added="onProviderAdded"
  />

  <!-- Modal Agente -->
  <AgentsAgentModal
    :open="agentModal"
    :agent="editingAgent"
    :providers="providers"
    @close="agentModal = false"
    @saved="onAgentSaved"
  />

  <!-- Modal Membros do Agente -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="membersModal" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="membersModal = false"></div>
        <div class="relative bg-surface border border-white/10 w-full max-w-md p-8 z-10">
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <p class="field-label mb-1">Agente</p>
          <h2 class="text-xl font-medium text-white mb-1 tracking-tight">{{ membersAgent?.name }}</h2>
          <p class="text-xs font-mono text-neutral-600 mb-6">
            Membros com acesso às conversas deste agente
          </p>

          <!-- Loading -->
          <div v-if="membersLoading" class="space-y-2 mb-6">
            <div v-for="i in 2" :key="i" class="h-12 bg-white/5 animate-pulse"></div>
          </div>

          <!-- Lista de membros -->
          <div v-else class="mb-6">
            <div v-if="memberships.length === 0" class="py-6 text-center border border-white/5">
              <Icon icon="solar:users-group-rounded-bold-duotone" class="text-3xl text-white/10 mb-2" />
              <p class="text-xs font-mono text-neutral-700">Nenhum membro atribuído</p>
              <p class="text-[10px] font-mono text-neutral-700 mt-1">
                Sem membros atribuídos, todos os owners e admins<br>têm acesso automaticamente
              </p>
            </div>
            <div v-else class="space-y-1">
              <div
                v-for="m in memberships"
                :key="m.id"
                class="flex items-center justify-between px-4 py-3 bg-canvas border border-white/5"
              >
                <div class="flex items-center gap-3">
                  <div class="w-7 h-7 bg-neutral-900 border border-white/10 flex items-center justify-center shrink-0">
                    <span class="text-[10px] font-mono text-neutral-400 uppercase">
                      {{ memberName(m.user_id)[0] ?? '?' }}
                    </span>
                  </div>
                  <div>
                    <p class="text-sm text-white">{{ memberName(m.user_id) }}</p>
                    <p class="text-[10px] font-mono text-neutral-600">{{ memberEmail(m.user_id) }}</p>
                  </div>
                </div>
                <button
                  @click="removeMember(m)"
                  class="p-1.5 text-neutral-300 hover:text-red-400 transition-colors"
                  title="Remover"
                >
                  <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
                </button>
              </div>
            </div>
          </div>

          <!-- Adicionar membro -->
          <div v-if="availableMembers.length > 0" class="flex gap-2">
            <select
              v-model="addMemberId"
              class="flex-1 bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2.5 outline-none focus:border-white/20"
            >
              <option :value="null" disabled>Selecionar membro...</option>
              <option v-for="m in availableMembers" :key="m.id" :value="m.id">
                {{ m.name || m.email }}
              </option>
            </select>
            <button
              @click="addMember"
              :disabled="!addMemberId || addMemberLoading"
              class="px-4 py-2.5 text-[10px] font-mono uppercase tracking-widest border border-accent/30 text-accent hover:bg-accent/5 transition-colors disabled:opacity-40"
            >
              {{ addMemberLoading ? '...' : 'Adicionar' }}
            </button>
          </div>
          <p v-else-if="!membersLoading" class="text-[10px] font-mono text-neutral-700 text-center">
            Todos os membros já estão atribuídos
          </p>

          <button
            @click="membersModal = false"
            class="mt-6 w-full py-2.5 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
