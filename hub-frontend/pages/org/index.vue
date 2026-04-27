<script setup lang="ts">
import { Icon } from '@iconify/vue'

const api = useApi()
const authStore = useAuthStore()
const { confirm: confirmDialog } = useConfirm()

const tab = ref<'members' | 'groups' | 'integrations' | 'horarios'>('members')

// ---- Members ----
const members = ref<any[]>([])
const groups = ref<any[]>([])
const loadingMembers = ref(true)

const fetchMembers = async () => {
  try {
    members.value = await api<any[]>('/api/org/members')
  } catch {}
}

const fetchGroups = async () => {
  try {
    groups.value = await api<any[]>('/api/org/permission-groups')
  } catch {}
}

onMounted(async () => {
  await Promise.all([fetchMembers(), fetchGroups()])
  if (isOwnerOrAdmin.value) {
    await fetchPipedrive()
  }
  loadingMembers.value = false
})

const { page: mbPage, totalPages: mbTotalPages, paged: pagedMembers, prev: mbPrev, next: mbNext, goTo: mbGoTo } = usePagination(members, 15)

// ---- Invite modal ----
const inviteModal = ref(false)
const inviteForm = reactive({ email: '', role: 'member', permission_group_id: null as number | null })
const inviteLoading = ref(false)
const inviteError = ref('')
const inviteSuccess = ref(false)

const openInvite = () => {
  inviteForm.email = ''
  inviteForm.role = 'member'
  inviteForm.permission_group_id = null
  inviteError.value = ''
  inviteSuccess.value = false
  inviteModal.value = true
}

const submitInvite = async () => {
  if (!inviteForm.email) return
  inviteLoading.value = true
  inviteError.value = ''
  try {
    await api('/api/org/invites', {
      method: 'POST',
      body: {
        email: inviteForm.email,
        role: inviteForm.role,
        permission_group_id: inviteForm.permission_group_id,
      },
    })
    inviteSuccess.value = true
  } catch (e: any) {
    inviteError.value = e?.data?.detail || 'Erro ao enviar convite'
  } finally {
    inviteLoading.value = false
  }
}

// ---- Edit member ----
const editMember = ref<any>(null)
const editForm = reactive({ role: '', permission_group_id: null as number | null })
const editLoading = ref(false)

const openEdit = (m: any) => {
  editMember.value = m
  editForm.role = m.role
  editForm.permission_group_id = m.permission_group?.id ?? null
}

const saveEdit = async () => {
  if (!editMember.value) return
  editLoading.value = true
  try {
    const updated = await api<any>(`/api/org/members/${editMember.value.id}`, {
      method: 'PATCH',
      body: { role: editForm.role, permission_group_id: editForm.permission_group_id },
    })
    const idx = members.value.findIndex(m => m.id === updated.id)
    if (idx !== -1) members.value[idx] = updated
    editMember.value = null
  } catch (e: any) {
    console.error(e)
  } finally {
    editLoading.value = false
  }
}

const removeMember = async (m: any) => {
  if (!await confirmDialog(`Remover ${m.name} da organização?`, { title: 'Remover membro' })) return
  try {
    await api(`/api/org/member/${m.id}`, { method: 'DELETE' })
    members.value = members.value.filter(x => x.id !== m.id)
  } catch {}
}

// ---- Groups ----
const groupModal = ref(false)
const groupEdit = ref<any>(null)
const groupForm = reactive({
  name: '',
  can_view_agents: false,
  can_create_agents: false,
  can_edit_agents: false,
  can_delete_agents: false,
  can_view_conversations: false,
  can_delete_conversations: false,
  can_export_conversations: false,
  view_pipedriveintegration: false,
  add_pipedriveintegration: false,
  delete_pipedriveintegration: false,
})
const groupLoading = ref(false)

const openGroupModal = (g: any = null) => {
  groupEdit.value = g
  if (g) {
    Object.assign(groupForm, {
      name: g.name ?? '',
      can_view_agents: g.can_view_agents,
      can_create_agents: g.can_create_agents,
      can_edit_agents: g.can_edit_agents,
      can_delete_agents: g.can_delete_agents,
      can_view_conversations: g.can_view_conversations,
      can_delete_conversations: g.can_delete_conversations,
      can_export_conversations: g.can_export_conversations,
      view_pipedriveintegration: g.view_pipedriveintegration,
      add_pipedriveintegration: g.add_pipedriveintegration,
      delete_pipedriveintegration: g.delete_pipedriveintegration,
    })
  } else {
    Object.assign(groupForm, {
      name: '',
      can_view_agents: false,
      can_create_agents: false,
      can_edit_agents: false,
      can_delete_agents: false,
      can_view_conversations: false,
      can_delete_conversations: false,
      can_export_conversations: false,
      view_pipedriveintegration: false,
      add_pipedriveintegration: false,
      delete_pipedriveintegration: false,
    })
  }
  groupModal.value = true
}

const saveGroup = async () => {
  groupLoading.value = true
  try {
    if (groupEdit.value) {
      const updated = await api<any>(`/api/org/permission-groups/${groupEdit.value.id}`, {
        method: 'PUT',
        body: { ...groupForm },
      })
      const idx = groups.value.findIndex(g => g.id === updated.id)
      if (idx !== -1) groups.value[idx] = updated
    } else {
      const created = await api<any>('/api/org/permission-groups', {
        method: 'POST',
        body: { ...groupForm },
      })
      groups.value.push(created)
    }
    groupModal.value = false
  } catch (e: any) {
    console.error(e)
  } finally {
    groupLoading.value = false
  }
}

const deleteGroup = async (g: any) => {
  if (!await confirmDialog(`Remover grupo "${g.name}"?`, { title: 'Remover grupo' })) return
  try {
    await api(`/api/org/permission-groups/${g.id}`, { method: 'DELETE' })
    groups.value = groups.value.filter(x => x.id !== g.id)
  } catch {}
}

// ---- Pipedrive Integration ----
type PipedriveStage = { id: number; name: string }
type PipedrivePipeline = { id: number; name: string; stages: PipedriveStage[] }
type PipedriveData = {
  is_configured: boolean
  api_key_masked?: string
  is_active: boolean
  updated_at?: string
  webhook_secret?: string
  sync_contacts: boolean
  auto_create_deal: boolean
  auto_close_deal: boolean
  deal_pipeline_id?: number | null
  deal_stage_id?: number | null
}

const pipedriveData = ref<PipedriveData | null>(null)
const pipedriveKey = ref('')
const pipedriveLoading = ref(false)
const pipedriveError = ref('')
const pipedriveSuccess = ref(false)

const pipelines = ref<PipedrivePipeline[]>([])
const pipelinesLoading = ref(false)
const configSaving = ref(false)
const configSuccess = ref(false)
const webhookCopied = ref(false)

const config = useRuntimeConfig()
const pipedriveWebhookUrl = computed(() =>
  pipedriveData.value?.webhook_secret
    ? `${config.public.apiBase}/api/webhooks/pipedrive/${pipedriveData.value.webhook_secret}`
    : ''
)

const copyWebhookUrl = async () => {
  if (!pipedriveWebhookUrl.value) return
  await navigator.clipboard.writeText(pipedriveWebhookUrl.value)
  webhookCopied.value = true
  setTimeout(() => { webhookCopied.value = false }, 2000)
}

const configForm = reactive({
  sync_contacts: false,
  auto_create_deal: false,
  auto_close_deal: false,
  deal_pipeline_id: null as number | null,
  deal_stage_id: null as number | null,
})

const selectedPipelineStages = computed<PipedriveStage[]>(() => {
  if (!configForm.deal_pipeline_id) return []
  return pipelines.value.find(p => p.id === configForm.deal_pipeline_id)?.stages ?? []
})

const fetchPipedrive = async () => {
  try {
    const data = await api<PipedriveData>('/api/org/integrations/pipedrive')
    pipedriveData.value = data
    configForm.sync_contacts = data.sync_contacts ?? false
    configForm.auto_create_deal = data.auto_create_deal ?? false
    configForm.auto_close_deal = data.auto_close_deal ?? false
    configForm.deal_pipeline_id = data.deal_pipeline_id ?? null
    configForm.deal_stage_id = data.deal_stage_id ?? null
    if (data.is_configured) fetchPipelines()
  } catch {}
}

const fetchPipelines = async () => {
  pipelinesLoading.value = true
  try {
    pipelines.value = await api<PipedrivePipeline[]>('/api/org/integrations/pipedrive/pipelines')
  } catch {} finally {
    pipelinesLoading.value = false
  }
}

const savePipedrive = async () => {
  if (!pipedriveKey.value.trim()) return
  pipedriveLoading.value = true
  pipedriveError.value = ''
  pipedriveSuccess.value = false
  try {
    const data = await api<PipedriveData>('/api/org/integrations/pipedrive', {
      method: 'PUT',
      body: { api_key: pipedriveKey.value.trim() },
    })
    pipedriveData.value = data
    pipedriveKey.value = ''
    pipedriveSuccess.value = true
    setTimeout(() => { pipedriveSuccess.value = false }, 3000)
    fetchPipelines()
  } catch (e: any) {
    pipedriveError.value = e?.data?.detail || 'Erro ao salvar integração'
  } finally {
    pipedriveLoading.value = false
  }
}

const saveConfig = async () => {
  configSaving.value = true
  configSuccess.value = false
  try {
    const data = await api<PipedriveData>('/api/org/integrations/pipedrive/config', {
      method: 'PATCH',
      body: { ...configForm },
    })
    pipedriveData.value = data
    configSuccess.value = true
    setTimeout(() => { configSuccess.value = false }, 3000)
  } catch {} finally {
    configSaving.value = false
  }
}

const onPipelineChange = () => {
  configForm.deal_stage_id = null
}

const removePipedrive = async () => {
  if (!await confirmDialog('Remover integração com Pipedrive?', { title: 'Remover integração' })) return
  try {
    await api('/api/org/integrations/pipedrive', { method: 'DELETE' })
    pipedriveData.value = { is_configured: false, is_active: false, sync_contacts: false, auto_create_deal: false, auto_close_deal: false }
    pipedriveKey.value = ''
    pipelines.value = []
    Object.assign(configForm, { sync_contacts: false, auto_create_deal: false, auto_close_deal: false, deal_pipeline_id: null, deal_stage_id: null })
  } catch {}
}

// ---- Horários de Atendimento ----
const WEEKDAYS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

const businessHours = ref<{ weekday: number; is_open: boolean; open_time: string; close_time: string }[]>([])
const hoursLoading = ref(false)
const hoursSaving = ref(false)
const hoursSaved = ref(false)

const fetchBusinessHours = async () => {
  hoursLoading.value = true
  try {
    businessHours.value = await api<any[]>('/api/org/business-hours/')
  } catch {}
  finally { hoursLoading.value = false }
}

const saveBusinessHours = async () => {
  hoursSaving.value = true
  hoursSaved.value = false
  try {
    businessHours.value = await api<any[]>('/api/org/business-hours/', {
      method: 'PUT',
      body: businessHours.value,
    })
    hoursSaved.value = true
    setTimeout(() => { hoursSaved.value = false }, 3000)
  } catch {}
  finally { hoursSaving.value = false }
}

watch(tab, (val) => {
  if (val === 'horarios' && businessHours.value.length === 0) fetchBusinessHours()
})

// ---- Helpers ----
const isOwnerOrAdmin = computed(() =>
  ['owner', 'admin'].includes(authStore.user?.role?.toLowerCase() ?? '')
)

const roleBadge = (role: string) => ({
  owner: { label: 'Owner', cls: 'text-accent bg-accent/10' },
  admin: { label: 'Admin', cls: 'text-blue-400 bg-blue-400/10' },
  member: { label: 'Membro', cls: 'text-neutral-400 bg-white/5' },
}[role.toLowerCase()] ?? { label: role, cls: 'text-neutral-400 bg-white/5' })

const permLabels: Record<string, string> = {
  can_view_agents: 'Ver agentes',
  can_create_agents: 'Criar agentes',
  can_edit_agents: 'Editar agentes',
  can_delete_agents: 'Excluir agentes',
  can_view_conversations: 'Ver todas as conversas',
  can_delete_conversations: 'Excluir conversas',
  can_export_conversations: 'Exportar conversas',
  view_pipedriveintegration: 'Ver integração - Pipedrive',
  add_pipedriveintegration: 'Configurar integração - Pipedrive',
  delete_pipedriveintegration: 'Remover integração - Pipedrive',
}
</script>

<template>
  <div class="p-4 md:p-8 max-w-5xl">
    <!-- Header -->
    <div class="mb-8">
      <p class="field-label mb-0.5">Configurações</p>
      <h1 class="text-2xl font-medium text-white tracking-tight">Organização</h1>
    </div>

    <!-- Tabs -->
    <div class="flex border-b border-white/5 mb-8">
      <button
        @click="tab = 'members'"
        class="pb-3 text-[10px] font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors whitespace-nowrap"
        :class="tab === 'members' ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
        style="margin-right: 40px"
      >
        Membros
      </button>
      <button
        @click="tab = 'groups'"
        class="pb-3 text-[10px] font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors whitespace-nowrap"
        :class="tab === 'groups' ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
        style="margin-right: 40px"
      >
        Grupos de Permissão
      </button>
      <button
        v-if="isOwnerOrAdmin"
        @click="tab = 'integrations'"
        class="pb-3 text-[10px] font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors whitespace-nowrap"
        :class="tab === 'integrations' ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
        style="margin-right: 40px"
      >
        Integrações
      </button>
      <button
        v-if="isOwnerOrAdmin"
        @click="tab = 'horarios'"
        class="pb-3 text-[10px] font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors whitespace-nowrap"
        :class="tab === 'horarios' ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
      >
        Horários
      </button>
    </div>

    <!-- ======================== MEMBROS ======================== -->
    <div v-if="tab === 'members'">
      <div class="flex items-center justify-between mb-5">
        <p class="text-xs font-mono text-neutral-500">{{ members.length }} membro{{ members.length !== 1 ? 's' : '' }}</p>
        <button
          v-if="isOwnerOrAdmin"
          @click="openInvite"
          class="btn-primary px-4 py-2"
        >
          <div class="corner-tl"></div>
          <div class="corner-br"></div>
          <span class="text-white text-xs font-mono uppercase tracking-wider flex items-center gap-2">
            <Icon icon="solar:user-plus-bold-duotone" class="text-sm" />
            Convidar
          </span>
        </button>
      </div>

      <div class="border border-white/5">
        <!-- Skeleton -->
        <div v-if="loadingMembers" class="divide-y divide-white/5">
          <div v-for="i in 3" :key="i" class="px-5 py-4 animate-pulse flex items-center gap-4">
            <div class="w-8 h-8 bg-white/5 rounded-full"></div>
            <div class="flex-1 space-y-2">
              <div class="h-3 bg-white/5 rounded w-32"></div>
              <div class="h-2 bg-white/5 rounded w-48"></div>
            </div>
          </div>
        </div>

        <div v-else class="divide-y divide-white/5">
          <div
            v-for="m in pagedMembers"
            :key="m.id"
            class="flex items-center gap-4 px-5 py-4"
          >
            <!-- Avatar -->
            <div class="w-10 h-10 bg-neutral-900 border border-white/10 flex items-center justify-center shrink-0">
              <span class="text-sm font-mono text-neutral-300 uppercase leading-none">{{ m.name?.[0] ?? '?' }}</span>
            </div>

            <!-- Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <p class="text-sm text-white font-medium">{{ m.name }}</p>
                <span
                  class="text-[9px] font-mono uppercase tracking-widest px-1.5 py-0.5"
                  :class="roleBadge(m.role).cls"
                >{{ roleBadge(m.role).label }}</span>
                <span v-if="m.permission_group" class="text-[9px] font-mono text-neutral-500 bg-white/5 px-1.5 py-0.5">
                  {{ m.permission_group.name }}
                </span>
              </div>
              <p class="text-[11px] font-mono text-neutral-600 mt-0.5">{{ m.email }}</p>
            </div>

            <!-- Actions -->
            <div v-if="isOwnerOrAdmin && m.id !== authStore.user?.id" class="flex items-center gap-1 shrink-0">
              <button
                @click="openEdit(m)"
                class="p-1.5 text-neutral-300 hover:text-white transition-colors"
                title="Editar"
              >
                <Icon icon="solar:pen-bold-duotone" class="text-base" />
              </button>
              <button
                @click="removeMember(m)"
                class="p-1.5 text-neutral-300 hover:text-red-400 transition-colors"
                title="Remover"
              >
                <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-base" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <AppPagination
        v-if="mbTotalPages > 1"
        :page="mbPage"
        :total-pages="mbTotalPages"
        @prev="mbPrev"
        @next="mbNext"
        @go-to="mbGoTo"
      />
    </div>

    <!-- ======================== GRUPOS ======================== -->
    <div v-if="tab === 'groups'">
      <div class="flex items-center justify-between mb-5">
        <p class="text-xs font-mono text-neutral-500">{{ groups.length }} grupo{{ groups.length !== 1 ? 's' : '' }}</p>
        <button
          v-if="isOwnerOrAdmin"
          @click="openGroupModal()"
          class="btn-primary px-4 py-2"
        >
          <div class="corner-tl"></div>
          <div class="corner-br"></div>
          <span class="text-white text-xs font-mono uppercase tracking-wider flex items-center gap-2">
            <Icon icon="solar:add-circle-bold-duotone" class="text-sm" />
            Novo grupo
          </span>
        </button>
      </div>

      <div v-if="groups.length === 0" class="flex flex-col items-center justify-center py-16 border border-white/5 text-center">
        <Icon icon="solar:shield-user-bold-duotone" class="text-4xl text-white/10 mb-3" />
        <p class="text-xs font-mono text-neutral-700">Nenhum grupo criado</p>
      </div>

      <div v-else class="grid gap-3">
        <div
          v-for="g in groups"
          :key="g.id"
          class="bg-surface border border-white/5 p-5"
        >
          <div class="flex items-start justify-between gap-4 mb-4">
            <div>
              <p class="text-sm text-white font-medium">{{ g.name }}</p>
              <p class="text-[10px] font-mono text-neutral-600 mt-0.5">
                {{ members.filter(m => m.permission_group?.id === g.id).length }} membro(s)
              </p>
            </div>
            <div v-if="isOwnerOrAdmin" class="flex items-center gap-1 shrink-0">
              <button @click="openGroupModal(g)" class="p-1.5 text-neutral-300 hover:text-white transition-colors">
                <Icon icon="solar:pen-bold-duotone" class="text-base" />
              </button>
              <button @click="deleteGroup(g)" class="p-1.5 text-neutral-300 hover:text-red-400 transition-colors">
                <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-base" />
              </button>
            </div>
          </div>

          <!-- Permissions grid -->
          <div class="grid grid-cols-2 gap-x-6 gap-y-1.5">
            <div
              v-for="[key, label] in Object.entries(permLabels)"
              :key="key"
              class="flex items-center gap-2"
            >
              <div
                class="w-1.5 h-1.5 rounded-full shrink-0"
                :class="g[key] ? 'bg-green-400' : 'bg-neutral-800'"
              ></div>
              <span class="text-[11px] font-mono" :class="g[key] ? 'text-neutral-400' : 'text-neutral-700'">
                {{ label }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ======================== INTEGRAÇÃO ======================== -->
    <div v-if="tab === 'integrations'" class="space-y-6 max-w-xl">

      <!-- Card Pipedrive: conexão -->
      <div class="bg-surface border border-white/5 p-8">
        <!-- Header -->
        <div class="flex items-center gap-4 mb-8">
          <div class="w-12 h-12 bg-neutral-900 border border-white/10 flex items-center justify-center shrink-0">
            <Icon icon="logos:pipedrive" class="text-2xl" />
          </div>
          <div>
            <h3 class="text-white font-medium">Pipedrive</h3>
            <p class="text-[11px] font-mono text-neutral-600 uppercase tracking-widest">CRM Integration</p>
          </div>
          <div class="ml-auto flex items-center gap-2">
            <div class="w-2 h-2 rounded-full" :class="pipedriveData?.is_configured ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' : 'bg-neutral-800'"></div>
            <span class="text-[10px] font-mono uppercase tracking-widest" :class="pipedriveData?.is_configured ? 'text-green-500' : 'text-neutral-600'">
              {{ pipedriveData?.is_configured ? 'Conectado' : 'Desconectado' }}
            </span>
          </div>
        </div>

        <!-- API Key info + input -->
        <div class="space-y-5">
          <div v-if="pipedriveData?.is_configured" class="bg-white/5 p-4 border border-white/5 flex items-center justify-between">
            <div>
              <p class="text-[10px] font-mono text-neutral-500 uppercase tracking-wider mb-1">Chave configurada</p>
              <p class="text-sm font-mono text-white tracking-widest">{{ pipedriveData.api_key_masked }}</p>
            </div>
            <p v-if="pipedriveData.updated_at" class="text-[10px] font-mono text-neutral-700">
              {{ new Date(pipedriveData.updated_at).toLocaleDateString('pt-BR') }}
            </p>
          </div>

          <div>
            <label class="field-label">{{ pipedriveData?.is_configured ? 'Atualizar API Key' : 'API Key' }}</label>
            <div class="input-wrapper">
              <input
                v-model="pipedriveKey"
                type="password"
                placeholder="Cole sua API key do Pipedrive..."
                class="input-field"
                @keydown.enter="savePipedrive"
              />
            </div>
            <p class="text-[10px] font-mono text-neutral-600 mt-2">
              Pipedrive → Configurações → Integrações → API.
            </p>
          </div>

          <p v-if="pipedriveError" class="text-xs font-mono text-red-400 bg-red-400/10 p-3 border border-red-400/20">{{ pipedriveError }}</p>
          <p v-if="pipedriveSuccess" class="text-xs font-mono text-green-400 bg-green-400/10 p-3 border border-green-400/20 flex items-center gap-2">
            <Icon icon="solar:check-circle-bold" /> Conectado com sucesso
          </p>

          <div class="flex items-center gap-4 pt-1">
            <button @click="savePipedrive" :disabled="pipedriveLoading || !pipedriveKey" class="btn-primary px-6 disabled:opacity-40">
              <div class="corner-tl"></div>
              <div class="corner-br"></div>
              <span class="text-white text-xs font-mono uppercase tracking-wider">
                {{ pipedriveLoading ? 'Verificando...' : (pipedriveData?.is_configured ? 'Atualizar chave' : 'Conectar') }}
              </span>
            </button>
            <button v-if="pipedriveData?.is_configured" @click="removePipedrive" class="text-[10px] font-mono uppercase tracking-widest text-neutral-600 hover:text-red-400 transition-colors">
              Remover
            </button>
          </div>
        </div>
      </div>

      <!-- Card configurações (só aparece quando conectado) -->
      <div v-if="pipedriveData?.is_configured" class="bg-surface border border-white/5 p-8 space-y-7">
        <div>
          <p class="text-xs font-mono text-neutral-400 uppercase tracking-widest mb-1">Comportamento</p>
          <p class="text-[10px] font-mono text-neutral-700">Defina o que acontece automaticamente no Pipedrive.</p>
        </div>

        <!-- Toggles -->
        <div class="space-y-4">
          <!-- sync_contacts -->
          <label class="flex items-center justify-between gap-4 cursor-pointer group">
            <div>
              <p class="text-xs font-mono text-neutral-300">Sincronizar contatos</p>
              <p class="text-[10px] font-mono text-neutral-600 mt-0.5">Ao criar ou atualizar um contato, sincroniza como Person no Pipedrive</p>
            </div>
            <button
              type="button"
              @click="configForm.sync_contacts = !configForm.sync_contacts"
              class="w-9 h-5 rounded-full relative transition-colors shrink-0"
              :class="configForm.sync_contacts ? 'bg-accent' : 'bg-neutral-800'"
            >
              <span class="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all" :class="configForm.sync_contacts ? 'left-4' : 'left-0.5'"></span>
            </button>
          </label>

          <!-- auto_create_deal -->
          <label class="flex items-center justify-between gap-4 cursor-pointer group">
            <div>
              <p class="text-xs font-mono text-neutral-300">Criar deal ao abrir conversa</p>
              <p class="text-[10px] font-mono text-neutral-600 mt-0.5">Cria um Deal no funil configurado ao iniciar nova conversa</p>
            </div>
            <button
              type="button"
              @click="configForm.auto_create_deal = !configForm.auto_create_deal"
              class="w-9 h-5 rounded-full relative transition-colors shrink-0"
              :class="configForm.auto_create_deal ? 'bg-accent' : 'bg-neutral-800'"
            >
              <span class="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all" :class="configForm.auto_create_deal ? 'left-4' : 'left-0.5'"></span>
            </button>
          </label>

          <!-- auto_close_deal -->
          <label class="flex items-center justify-between gap-4 cursor-pointer group">
            <div>
              <p class="text-xs font-mono text-neutral-300">Fechar deal ao encerrar conversa</p>
              <p class="text-[10px] font-mono text-neutral-600 mt-0.5">Marca o Deal como ganho quando a conversa é fechada</p>
            </div>
            <button
              type="button"
              @click="configForm.auto_close_deal = !configForm.auto_close_deal"
              class="w-9 h-5 rounded-full relative transition-colors shrink-0"
              :class="configForm.auto_close_deal ? 'bg-accent' : 'bg-neutral-800'"
            >
              <span class="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all" :class="configForm.auto_close_deal ? 'left-4' : 'left-0.5'"></span>
            </button>
          </label>
        </div>

        <!-- Funil e etapa (visível quando auto_create_deal ativo) -->
        <Transition name="fade">
          <div v-if="configForm.auto_create_deal" class="space-y-4 pt-2 border-t border-white/5">
            <p class="text-[10px] font-mono text-neutral-500 uppercase tracking-widest pt-2">Destino dos deals</p>

            <!-- Pipeline -->
            <div>
              <label class="field-label">Funil</label>
              <div class="bg-surface border border-white/10 rounded-full py-3 pl-5 pr-4 hover:border-accent/50 transition-colors" :class="pipelinesLoading ? 'opacity-50' : ''">
                <select
                  v-model="configForm.deal_pipeline_id"
                  @change="onPipelineChange"
                  class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer"
                  :disabled="pipelinesLoading"
                >
                  <option :value="null" class="bg-surface text-neutral-500">{{ pipelinesLoading ? 'Carregando...' : 'Selecione um funil' }}</option>
                  <option v-for="p in pipelines" :key="p.id" :value="p.id" class="bg-surface">{{ p.name }}</option>
                </select>
              </div>
            </div>

            <!-- Stage -->
            <div v-if="configForm.deal_pipeline_id">
              <label class="field-label">Etapa inicial</label>
              <div class="bg-surface border border-white/10 rounded-full py-3 pl-5 pr-4 hover:border-accent/50 transition-colors">
                <select
                  v-model="configForm.deal_stage_id"
                  class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer"
                >
                  <option :value="null" class="bg-surface text-neutral-500">Selecione uma etapa</option>
                  <option v-for="s in selectedPipelineStages" :key="s.id" :value="s.id" class="bg-surface">{{ s.name }}</option>
                </select>
              </div>
            </div>
          </div>
        </Transition>

        <!-- Webhook URL -->
        <div class="pt-2 border-t border-white/5 space-y-2">
          <p class="text-xs font-mono text-neutral-400 uppercase tracking-widest">Webhook — Pipedrive → ChatlyAi</p>
          <p class="text-[10px] font-mono text-neutral-600">Cole esta URL nas configurações de webhook do Pipedrive para sincronizar persons criados/atualizados/deletados.</p>
          <div class="flex items-center gap-2">
            <code class="flex-1 bg-black/30 border border-white/5 px-3 py-2 text-[10px] font-mono text-neutral-400 truncate select-all">
              {{ pipedriveWebhookUrl }}
            </code>
            <button @click="copyWebhookUrl" class="shrink-0 text-neutral-500 hover:text-accent transition-colors" title="Copiar URL">
              <Icon :icon="webhookCopied ? 'solar:check-circle-bold' : 'solar:copy-bold-duotone'" class="text-base" />
            </button>
          </div>
        </div>

        <!-- Feedback + salvar -->
        <p v-if="configSuccess" class="text-xs font-mono text-green-400 bg-green-400/10 p-3 border border-green-400/20 flex items-center gap-2">
          <Icon icon="solar:check-circle-bold" /> Configuração salva
        </p>

        <button @click="saveConfig" :disabled="configSaving" class="btn-primary px-6 disabled:opacity-40">
          <div class="corner-tl"></div>
          <div class="corner-br"></div>
          <span class="text-white text-xs font-mono uppercase tracking-wider">
            {{ configSaving ? 'Salvando...' : 'Salvar configuração' }}
          </span>
        </button>
      </div>
    </div>

    <!-- ====================== HORÁRIOS ====================== -->
    <div v-if="tab === 'horarios'">
      <div class="mb-6">
        <p class="text-xs font-mono text-neutral-500 mt-1">
          Define os dias e horários em que a organização está em atendimento.
          Agentes com follow-up configurado respeitarão esses horários quando a opção estiver ativada.
        </p>
      </div>

      <!-- Skeleton -->
      <div v-if="hoursLoading" class="space-y-2">
        <div v-for="i in 7" :key="i" class="h-12 bg-white/5 animate-pulse" />
      </div>

      <div v-else class="space-y-1">
        <div
          v-for="row in businessHours"
          :key="row.weekday"
          class="flex items-center gap-4 px-4 py-3 border border-white/5 bg-surface"
          :class="row.is_open ? '' : 'opacity-60'"
        >
          <!-- Dia -->
          <span class="w-20 text-xs font-mono text-white shrink-0">{{ WEEKDAYS[row.weekday] }}</span>

          <!-- Toggle aberto/fechado -->
          <button
            type="button"
            @click="row.is_open = !row.is_open"
            class="relative w-9 h-5 rounded-full transition-colors flex-shrink-0"
            :class="row.is_open ? 'bg-accent' : 'bg-neutral-800'"
          >
            <span
              class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
              :class="row.is_open ? 'translate-x-4' : 'translate-x-0'"
            />
          </button>
          <span class="text-[10px] font-mono w-14 shrink-0" :class="row.is_open ? 'text-green-400' : 'text-neutral-600'">
            {{ row.is_open ? 'Aberto' : 'Fechado' }}
          </span>

          <!-- Horários -->
          <div class="flex items-center gap-2 flex-1">
            <input
              v-model="row.open_time"
              type="time"
              :disabled="!row.is_open"
              class="bg-canvas border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20 disabled:opacity-30 disabled:cursor-not-allowed w-28"
            />
            <span class="text-neutral-600 text-xs font-mono shrink-0">até</span>
            <input
              v-model="row.close_time"
              type="time"
              :disabled="!row.is_open"
              class="bg-canvas border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20 disabled:opacity-30 disabled:cursor-not-allowed w-28"
            />
          </div>
        </div>
      </div>

      <!-- Feedback + salvar -->
      <div class="mt-5 flex items-center gap-4">
        <button
          @click="saveBusinessHours"
          :disabled="hoursSaving || hoursLoading"
          class="btn-primary px-6 disabled:opacity-40"
        >
          <div class="corner-tl"></div>
          <div class="corner-br"></div>
          <span class="text-white text-xs font-mono uppercase tracking-wider">
            {{ hoursSaving ? 'Salvando...' : 'Salvar horários' }}
          </span>
        </button>
        <p v-if="hoursSaved" class="text-xs font-mono text-green-400 flex items-center gap-1.5">
          <Icon icon="solar:check-circle-bold" /> Salvo
        </p>
      </div>
    </div>
  </div>

  <!-- =================== MODAL CONVIDAR =================== -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="inviteModal" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="inviteModal = false"></div>
        <div class="relative bg-surface border border-white/10 w-full max-w-sm p-8 z-10">
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <p class="field-label mb-1">Organização</p>
          <h2 class="text-xl font-medium text-white mb-6 tracking-tight">Convidar membro</h2>

          <div v-if="inviteSuccess" class="text-center py-4">
            <Icon icon="solar:check-circle-bold-duotone" class="text-4xl text-green-400 mx-auto mb-3" />
            <p class="text-sm text-white mb-1">Convite enviado!</p>
            <p class="text-xs font-mono text-neutral-600">O link foi enviado para {{ inviteForm.email }}</p>
            <button @click="inviteModal = false" class="mt-5 text-xs font-mono text-neutral-300 hover:text-white transition-colors uppercase tracking-wider">
              Fechar
            </button>
          </div>

          <form v-else @submit.prevent="submitInvite" class="space-y-4">
            <div>
              <label class="field-label">E-mail <span class="text-red-500">*</span></label>
              <div class="input-wrapper">
                <input v-model="inviteForm.email" type="email" required placeholder="nome@empresa.com" class="input-field" />
              </div>
            </div>

            <div>
              <label class="field-label">Função</label>
              <div class="bg-surface border border-white/10 rounded-full py-3 pl-6 pr-4 hover:border-accent/50 transition-colors">
                <select v-model="inviteForm.role" class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer">
                  <option value="member" class="bg-surface">Membro</option>
                  <option value="admin" class="bg-surface">Admin</option>
                </select>
              </div>
            </div>

            <div>
              <label class="field-label">Grupo de permissão <span class="text-neutral-700 normal-case">(opcional)</span></label>
              <div class="bg-surface border border-white/10 rounded-full py-3 pl-6 pr-4 hover:border-accent/50 transition-colors">
                <select v-model="inviteForm.permission_group_id" class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer">
                  <option :value="null" class="bg-surface text-neutral-500">Sem grupo</option>
                  <option v-for="g in groups" :key="g.id" :value="g.id" class="bg-surface">{{ g.name }}</option>
                </select>
              </div>
            </div>

            <p v-if="inviteError" class="text-xs font-mono text-red-400">{{ inviteError }}</p>

            <div class="flex gap-3 pt-1">
              <button type="button" @click="inviteModal = false" class="flex-1 py-3 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors">
                Cancelar
              </button>
              <button type="submit" :disabled="inviteLoading || !inviteForm.email" class="btn-primary flex-1 disabled:opacity-50">
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">
                  {{ inviteLoading ? 'Enviando...' : 'Enviar convite' }}
                </span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- =================== MODAL EDITAR MEMBRO =================== -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="editMember" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="editMember = null"></div>
        <div class="relative bg-surface border border-white/10 w-full max-w-sm p-8 z-10">
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <p class="field-label mb-1">Membro</p>
          <h2 class="text-xl font-medium text-white mb-1 tracking-tight">{{ editMember.name }}</h2>
          <p class="text-xs font-mono text-neutral-600 mb-6">{{ editMember.email }}</p>

          <div class="space-y-4">
            <div>
              <label class="field-label">Função</label>
              <div class="bg-surface border border-white/10 rounded-full py-3 pl-6 pr-4 hover:border-accent/50 transition-colors">
                <select v-model="editForm.role" class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer">
                  <option value="member" class="bg-surface">Membro</option>
                  <option value="admin" class="bg-surface">Admin</option>
                </select>
              </div>
            </div>

            <div>
              <label class="field-label">Grupo de permissão</label>
              <div class="bg-surface border border-white/10 rounded-full py-3 pl-6 pr-4 hover:border-accent/50 transition-colors">
                <select v-model="editForm.permission_group_id" class="bg-transparent border-none outline-none text-white text-sm w-full font-mono appearance-none cursor-pointer">
                  <option :value="null" class="bg-surface text-neutral-500">Sem grupo</option>
                  <option v-for="g in groups" :key="g.id" :value="g.id" class="bg-surface">{{ g.name }}</option>
                </select>
              </div>
            </div>

            <div class="flex gap-3 pt-1">
              <button @click="editMember = null" class="flex-1 py-3 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors">
                Cancelar
              </button>
              <button @click="saveEdit" :disabled="editLoading" class="btn-primary flex-1 disabled:opacity-50">
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">
                  {{ editLoading ? 'Salvando...' : 'Salvar' }}
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- =================== MODAL GRUPO =================== -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="groupModal" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="groupModal = false"></div>
        <div class="relative bg-surface border border-white/10 w-full max-w-sm p-8 z-10">
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <p class="field-label mb-1">Grupos</p>
          <h2 class="text-xl font-medium text-white mb-6 tracking-tight">
            {{ groupEdit ? 'Editar grupo' : 'Novo grupo' }}
          </h2>

          <form @submit.prevent="saveGroup" class="space-y-5">
            <div>
              <label class="field-label">Nome <span class="text-red-500">*</span></label>
              <div class="input-wrapper">
                <input v-model="groupForm.name" type="text" required placeholder="Ex: Suporte" class="input-field" />
              </div>
            </div>

            <div>
              <label class="field-label mb-3 block text-neutral-500 uppercase tracking-widest text-[9px]">Agentes</label>
              <div class="space-y-2.5">
                <label
                  v-for="key in ['can_view_agents', 'can_create_agents', 'can_edit_agents', 'can_delete_agents']"
                  :key="key"
                  class="flex items-center gap-3 cursor-pointer group"
                >
                  <div
                    class="w-4 h-4 border shrink-0 flex items-center justify-center transition-colors"
                    :class="(groupForm as any)[key] ? 'border-accent bg-accent/10' : 'border-white/10 group-hover:border-white/20'"
                    @click="(groupForm as any)[key] = !(groupForm as any)[key]"
                  >
                    <Icon v-if="(groupForm as any)[key]" icon="solar:check-read-bold" class="text-[10px] text-accent" />
                  </div>
                  <span class="text-xs font-mono text-neutral-400">{{ permLabels[key] }}</span>
                </label>
              </div>
            </div>

            <div>
              <label class="field-label mb-3 block text-neutral-500 uppercase tracking-widest text-[9px]">Conversas</label>
              <div class="space-y-2.5">
                <label
                  v-for="key in ['can_view_conversations', 'can_delete_conversations', 'can_export_conversations']"
                  :key="key"
                  class="flex items-center gap-3 cursor-pointer group"
                >
                  <div
                    class="w-4 h-4 border shrink-0 flex items-center justify-center transition-colors"
                    :class="(groupForm as any)[key] ? 'border-accent bg-accent/10' : 'border-white/10 group-hover:border-white/20'"
                    @click="(groupForm as any)[key] = !(groupForm as any)[key]"
                  >
                    <Icon v-if="(groupForm as any)[key]" icon="solar:check-read-bold" class="text-[10px] text-accent" />
                  </div>
                  <span class="text-xs font-mono text-neutral-400">{{ permLabels[key] }}</span>
                </label>
              </div>
            </div>

            <div>
              <label class="field-label mb-3 block text-neutral-500 uppercase tracking-widest text-[9px]">Pipedrive</label>
              <div class="space-y-2.5">
                <label
                  v-for="key in ['view_pipedriveintegration', 'add_pipedriveintegration', 'delete_pipedriveintegration']"
                  :key="key"
                  class="flex items-center gap-3 cursor-pointer group"
                >
                  <div
                    class="w-4 h-4 border shrink-0 flex items-center justify-center transition-colors"
                    :class="(groupForm as any)[key] ? 'border-accent bg-accent/10' : 'border-white/10 group-hover:border-white/20'"
                    @click="(groupForm as any)[key] = !(groupForm as any)[key]"
                  >
                    <Icon v-if="(groupForm as any)[key]" icon="solar:check-read-bold" class="text-[10px] text-accent" />
                  </div>
                  <span class="text-xs font-mono text-neutral-400">{{ permLabels[key] }}</span>
                </label>
              </div>
            </div>

            <div class="flex gap-3 pt-1">
              <button type="button" @click="groupModal = false" class="flex-1 py-3 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors">
                Cancelar
              </button>
              <button type="submit" :disabled="groupLoading || !groupForm.name" class="btn-primary flex-1 disabled:opacity-50">
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">
                  {{ groupLoading ? 'Salvando...' : (groupEdit ? 'Salvar' : 'Criar') }}
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
