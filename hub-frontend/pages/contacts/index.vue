<script setup lang="ts">
import { Icon } from '@iconify/vue'

useHead({ title: 'Contatos' })

const api = useApi()
const { confirm: confirmDialog } = useConfirm()

const contacts = ref<any[]>([])
const loading = ref(true)
const search = ref('')
const filterLabelId = ref<number | null>(null)
const selectedId = ref<number | null>(null)
const selectedContact = computed(() => contacts.value.find(c => c.id === selectedId.value) ?? null)

const labelsStore = useLabelsStore()
onMounted(() => labelsStore.fetchLabels())

const filtered = computed(() => {
  let list = contacts.value
  if (filterLabelId.value) list = list.filter(c => c.labels?.some((l: any) => l.id === filterLabelId.value))
  const q = search.value.toLowerCase().trim()
  if (!q) return list
  return list.filter(c =>
    c.name?.toLowerCase().includes(q) ||
    c.phone?.toLowerCase().includes(q) ||
    c.email?.toLowerCase().includes(q)
  )
})

const visibleCount = ref(30)
const sentinelRef = ref<HTMLElement>()
const visibleContacts = computed(() => filtered.value.slice(0, visibleCount.value))
watch(filtered, () => { visibleCount.value = 30 })

const fetchContacts = async () => {
  try {
    contacts.value = await api<any[]>('/api/contacts/')
  } catch {}
  finally { loading.value = false }
}

let ctObserver: IntersectionObserver | null = null
onMounted(() => {
  fetchContacts()
  ctObserver = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting && visibleCount.value < filtered.value.length)
      visibleCount.value += 30
  }, { threshold: 0.1 })
  watch(sentinelRef, el => { if (el) ctObserver?.observe(el) }, { immediate: true })
})
onUnmounted(() => ctObserver?.disconnect())

// ---- Helpers custom fields ----
type Field = { key: string; value: string }

const dictToFields = (dict: Record<string, any>): Field[] =>
  Object.entries(dict ?? {}).map(([key, value]) => ({ key, value: String(value ?? '') }))

const fieldsToDct = (fields: Field[]): Record<string, string> =>
  Object.fromEntries(fields.filter(f => f.key.trim()).map(f => [f.key.trim(), f.value]))

// ---- Create/Edit modal ----
const importModal = ref(false)

const onImported = async () => {
  await fetchContacts()
}

const modal = ref(false)
const editContact = ref<any>(null)
const form = reactive({
  name: '',
  phone: '',
  email: '',
  customFields: [] as Field[],
})
const formLoading = ref(false)
const formError = ref('')

const openCreate = () => {
  editContact.value = null
  form.name = ''
  form.phone = ''
  form.email = ''
  form.customFields = []
  formError.value = ''
  modal.value = true
}

const openEdit = (c: any) => {
  editContact.value = c
  form.name = c.name ?? ''
  form.phone = c.phone ?? ''
  form.email = c.email ?? ''
  form.customFields = dictToFields(c.custom_fields)
  formError.value = ''
  modal.value = true
}

const addField = () => form.customFields.push({ key: '', value: '' })
const removeField = (i: number) => form.customFields.splice(i, 1)

const saveContact = async () => {
  formLoading.value = true
  formError.value = ''
  try {
    const body = {
      name: form.name,
      phone: form.phone,
      email: form.email,
      custom_fields: fieldsToDct(form.customFields),
    }
    if (editContact.value) {
      const updated = await api<any>(`/api/contacts/${editContact.value.id}`, {
        method: 'PATCH',
        body,
      })
      const idx = contacts.value.findIndex(c => c.id === updated.id)
      if (idx !== -1) contacts.value[idx] = updated
      if (selectedId.value === updated.id) selectedId.value = updated.id
    } else {
      const created = await api<any>('/api/contacts/', {
        method: 'POST',
        body,
      })
      contacts.value.unshift(created)
      selectedId.value = created.id
    }
    modal.value = false
  } catch (e: any) {
    formError.value = e?.data?.detail || 'Erro ao salvar contato'
  } finally {
    formLoading.value = false
  }
}

const deleteContact = async (c: any) => {
  if (!await confirmDialog(`Remover "${c.name}"?`, { title: 'Remover contato' })) return
  try {
    await api(`/api/contacts/${c.id}`, { method: 'DELETE' })
    contacts.value = contacts.value.filter(x => x.id !== c.id)
    if (selectedId.value === c.id) selectedId.value = null
  } catch {}
}

const mobileView = ref<'list' | 'detail'>('list')

const selectContact = (id: number) => {
  selectedId.value = id
  mobileView.value = 'detail'
}

// ---- Conversations history ----
const conversations = ref<any[]>([])
const loadingConvs = ref(false)

watch(selectedId, async (id) => {
  if (!id) { conversations.value = []; return }
  loadingConvs.value = true
  try {
    conversations.value = await api<any[]>(`/api/conversations/?contact_id=${id}`)
  } catch {
    conversations.value = []
  } finally {
    loadingConvs.value = false
  }
})

// ---- Helpers ----
const formatDate = (dt: string) =>
  new Date(dt).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })

const formatTime = (dt: string) => {
  const d = new Date(dt)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return 'agora'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m atrás`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h atrás`
  return formatDate(dt)
}
</script>

<template>
  <div class="flex overflow-hidden h-full">

    <!-- Left: lista de contatos -->
    <div
      class="border-r border-white/5 flex flex-col bg-canvas shrink-0 w-full md:w-72"
      :class="mobileView === 'list' ? 'flex' : 'hidden md:flex'"
    >
      <!-- Header -->
      <div class="px-5 pt-6 pb-3 border-b border-white/5">
        <div class="flex items-center justify-between">
          <div>
            <p class="field-label mb-0.5">CRM</p>
            <h1 class="text-lg font-medium text-white tracking-tight">Contatos</h1>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="importModal = true"
              class="w-7 h-7 flex items-center justify-center border border-white/10 text-neutral-300 hover:border-white/20 hover:text-white transition-colors"
              title="Importar CSV"
            >
              <Icon icon="solar:import-bold-duotone" class="text-base" />
            </button>
            <button
              @click="openCreate"
              class="w-7 h-7 flex items-center justify-center border border-white/10 text-neutral-300 hover:border-accent/50 hover:text-accent transition-colors"
              title="Novo contato"
            >
              <Icon icon="solar:add-circle-bold-duotone" class="text-base" />
            </button>
          </div>
        </div>

        <!-- Search -->
        <div class="mt-3 relative">
          <Icon icon="solar:magnifer-bold-duotone" class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-700 text-sm pointer-events-none" />
          <input
            v-model="search"
            type="text"
            placeholder="Buscar..."
            class="w-full bg-surface border border-white/5 pl-8 pr-3 py-2 text-xs font-mono text-white placeholder-neutral-700 outline-none focus:border-white/10"
          />
        </div>

        <!-- Filtro por etiqueta -->
        <div v-if="labelsStore.labels.length > 0" class="mt-2 flex flex-wrap gap-1">
          <button
            @click="filterLabelId = null"
            class="px-2 py-0.5 text-[9px] font-mono uppercase tracking-widest border transition-colors"
            :class="filterLabelId === null ? 'border-white/20 text-white bg-white/5' : 'border-white/5 text-neutral-600 hover:text-neutral-400'"
          >
            Todas
          </button>
          <button
            v-for="label in labelsStore.labels"
            :key="label.id"
            @click="filterLabelId = filterLabelId === label.id ? null : label.id"
            class="px-2 py-0.5 text-[9px] font-mono uppercase tracking-widest border transition-colors"
            :class="filterLabelId === label.id ? 'text-white' : 'text-neutral-600 hover:text-neutral-400'"
            :style="filterLabelId === label.id ? `border-color: ${label.color}50; background: ${label.color}15; color: ${label.color}` : 'border-color: rgba(255,255,255,0.05)'"
          >
            {{ label.name }}
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
          <Icon icon="solar:users-group-rounded-bold-duotone" class="text-4xl text-white/10 mb-3" />
          <p class="text-xs font-mono text-neutral-700">Nenhum contato encontrado</p>
        </div>

        <button
          v-else
          v-for="c in visibleContacts"
          :key="c.id"
          @click="selectContact(c.id)"
          class="w-full px-5 py-3.5 text-left border-b border-white/5 transition-colors hover:bg-white/[0.02] relative"
          :class="selectedId === c.id ? 'bg-white/[0.04]' : ''"
        >
          <div v-if="selectedId === c.id" class="absolute left-0 top-0 bottom-0 w-0.5 bg-accent"></div>
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 bg-neutral-900 border border-white/10 flex items-center justify-center shrink-0">
              <span class="text-xs font-mono text-neutral-300 uppercase leading-none">{{ c.name?.[0] ?? '?' }}</span>
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-sm text-white font-medium truncate">{{ c.name }}</p>
              <p class="text-[11px] font-mono text-neutral-600 truncate">{{ c.phone || c.email || '—' }}</p>
              <div v-if="c.labels?.length" class="flex flex-wrap gap-1 mt-1">
                <LabelsLabelBadge
                  v-for="l in c.labels.slice(0, 3)"
                  :key="l.id"
                  :name="l.name"
                  :color="l.color"
                />
                <span v-if="c.labels.length > 3" class="text-[9px] font-mono text-neutral-700">+{{ c.labels.length - 3 }}</span>
              </div>
            </div>
          </div>
        </button>
        <div v-if="visibleCount < filtered.length" ref="sentinelRef" class="h-4"></div>
      </div>
    </div>

    <!-- Right: detalhe do contato -->
    <div
      class="flex-1 overflow-y-auto scrollbar-thin bg-canvas"
      :class="mobileView === 'detail' ? 'block' : 'hidden md:block'"
    >
      <!-- Nenhum selecionado -->
      <div v-if="!selectedContact" class="h-full flex flex-col items-center justify-center text-center">
        <Icon icon="solar:user-bold-duotone" class="text-6xl text-white/5 mb-4" />
        <p class="text-sm font-mono text-neutral-700">Selecione um contato</p>
      </div>

      <template v-else>
        <!-- Botão voltar (mobile) -->
        <div class="md:hidden px-4 pt-4">
          <button
            @click="mobileView = 'list'"
            class="flex items-center gap-1.5 text-xs font-mono text-neutral-400 hover:text-white transition-colors"
          >
            <Icon icon="solar:arrow-left-bold-duotone" class="text-sm" />
            Contatos
          </button>
        </div>
        <div class="max-w-2xl mx-auto px-4 md:px-8 py-4 md:py-8">
          <!-- Header do contato -->
          <div class="flex items-start justify-between mb-8">
            <div class="flex items-center gap-4">
              <div class="w-14 h-14 bg-neutral-900 border border-white/10 flex items-center justify-center shrink-0">
                <span class="text-xl font-mono text-neutral-300 uppercase leading-none">{{ selectedContact.name?.[0] ?? '?' }}</span>
              </div>
              <div>
                <h2 class="text-xl font-medium text-white tracking-tight">{{ selectedContact.name }}</h2>
                <p class="text-xs font-mono text-neutral-600 mt-0.5">
                  Criado em {{ formatDate(selectedContact.created_at) }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-1">
              <button
                @click="openEdit(selectedContact)"
                class="p-2 text-neutral-300 hover:text-white transition-colors"
                title="Editar"
              >
                <Icon icon="solar:pen-bold-duotone" class="text-base" />
              </button>
              <button
                @click="deleteContact(selectedContact)"
                class="p-2 text-neutral-300 hover:text-red-400 transition-colors"
                title="Remover"
              >
                <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-base" />
              </button>
            </div>
          </div>

          <!-- Info cards -->
          <div class="grid grid-cols-2 gap-3 mb-6">
            <div class="bg-surface border border-white/5 px-4 py-3">
              <p class="field-label mb-1">Telefone</p>
              <p class="text-sm text-white font-mono">{{ selectedContact.phone || '—' }}</p>
            </div>
            <div class="bg-surface border border-white/5 px-4 py-3">
              <p class="field-label mb-1">E-mail</p>
              <p class="text-sm text-white font-mono truncate">{{ selectedContact.email || '—' }}</p>
            </div>
          </div>

          <!-- Etiquetas -->
          <div class="mb-6">
            <p class="field-label mb-2">Etiquetas</p>
            <LabelsLabelSelector
              entity-type="contact"
              :entity-id="selectedContact.id"
              :labels="selectedContact.labels ?? []"
              @updated="(labels) => { const c = contacts.find(x => x.id === selectedContact.id); if (c) c.labels = labels }"
            />
          </div>

          <!-- Campos personalizados -->
          <div class="mb-8">
            <div class="flex items-center justify-between mb-3">
              <p class="field-label mb-0">Campos personalizados</p>
              <button
                @click="openEdit(selectedContact)"
                class="text-[10px] font-mono text-neutral-600 hover:text-accent transition-colors"
              >
                + Editar campos
              </button>
            </div>
            <div
              v-if="Object.keys(selectedContact.custom_fields ?? {}).length === 0"
              class="flex items-center gap-2 py-3 border border-white/5 px-4"
            >
              <p class="text-xs font-mono text-neutral-700">Nenhum campo personalizado —</p>
              <button @click="openEdit(selectedContact)" class="text-xs font-mono text-accent hover:text-orange-300 transition-colors">
                adicionar
              </button>
            </div>
            <div v-else class="grid grid-cols-2 gap-3">
              <div
                v-for="[key, val] in Object.entries(selectedContact.custom_fields)"
                :key="key"
                class="bg-surface border border-white/5 px-4 py-3"
              >
                <p class="field-label mb-1">{{ key }}</p>
                <p class="text-sm text-white font-mono truncate">{{ val || '—' }}</p>
              </div>
            </div>
          </div>

          <!-- Histórico de conversas -->
          <div>
            <p class="field-label mb-4">Histórico de conversas</p>

            <div v-if="loadingConvs" class="space-y-2">
              <div v-for="i in 3" :key="i" class="h-16 bg-white/5 animate-pulse"></div>
            </div>

            <div v-else-if="conversations.length === 0" class="flex flex-col items-center justify-center py-12 border border-white/5 text-center">
              <Icon icon="solar:chat-round-dots-bold-duotone" class="text-3xl text-white/10 mb-2" />
              <p class="text-xs font-mono text-neutral-700">Nenhuma conversa</p>
            </div>

            <div v-else class="space-y-2">
              <NuxtLink
                v-for="conv in conversations"
                :key="conv.id"
                to="/conversations"
                class="flex items-center justify-between px-4 py-3 bg-surface border border-white/5 hover:border-white/10 transition-colors group"
              >
                <div class="flex items-center gap-3 min-w-0">
                  <div
                    class="w-1.5 h-1.5 rounded-full shrink-0"
                    :class="conv.status === 'open' ? 'bg-green-400' : 'bg-neutral-700'"
                  ></div>
                  <div class="min-w-0">
                    <p class="text-xs text-white font-mono">
                      {{ conv.agent?.name || 'Sem agente' }}
                    </p>
                    <p class="text-[10px] font-mono text-neutral-600">
                      {{ conv.status === 'open' ? 'Aberta' : 'Fechada' }}
                    </p>
                  </div>
                </div>
                <div class="text-right shrink-0">
                  <p class="text-[10px] font-mono text-neutral-700">{{ formatTime(conv.started_at) }}</p>
                  <Icon icon="solar:arrow-right-bold-duotone" class="text-neutral-700 group-hover:text-neutral-400 transition-colors text-sm mt-0.5 ml-auto" />
                </div>
              </NuxtLink>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>

  <!-- Modal importar CSV -->
  <ContactsImportModal
    v-if="importModal"
    @close="importModal = false"
    @imported="onImported"
  />

  <!-- Modal criar/editar -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modal" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="modal = false"></div>
        <div class="relative bg-surface border border-white/10 w-full max-w-md max-h-[90vh] flex flex-col z-10">
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <!-- Header fixo -->
          <div class="px-8 pt-8 pb-4 shrink-0">
            <p class="field-label mb-1">Contatos</p>
            <h2 class="text-xl font-medium text-white tracking-tight">
              {{ editContact ? 'Editar contato' : 'Novo contato' }}
            </h2>
          </div>

          <!-- Conteúdo com scroll -->
          <form @submit.prevent="saveContact" class="flex flex-col flex-1 min-h-0">
            <div class="overflow-y-auto flex-1 px-8 space-y-4">
              <div>
                <label class="field-label">Nome</label>
                <div class="input-wrapper">
                  <input v-model="form.name" type="text" placeholder="João Silva" class="input-field" />
                </div>
              </div>
              <div>
                <label class="field-label">Telefone</label>
                <div class="input-wrapper">
                  <input v-model="form.phone" type="text" placeholder="5511999999999" class="input-field" />
                </div>
              </div>
              <div>
                <label class="field-label">E-mail</label>
                <div class="input-wrapper">
                  <input v-model="form.email" type="email" placeholder="joao@email.com" class="input-field" />
                </div>
              </div>

              <!-- Campos personalizados -->
              <div class="pt-2">
                <div class="flex items-center justify-between mb-3">
                  <label class="field-label mb-0">Campos personalizados</label>
                  <button
                    type="button"
                    @click="addField"
                    class="text-[10px] font-mono text-accent hover:text-orange-300 transition-colors flex items-center gap-1"
                  >
                    <Icon icon="solar:add-circle-bold-duotone" class="text-sm" />
                    Adicionar campo
                  </button>
                </div>

                <div v-if="form.customFields.length === 0" class="py-4 border border-white/5 flex items-center justify-center">
                  <p class="text-xs font-mono text-neutral-700">Nenhum campo personalizado</p>
                </div>

                <div v-else class="space-y-2">
                  <div
                    v-for="(f, i) in form.customFields"
                    :key="i"
                    class="flex items-center gap-2"
                  >
                    <input
                      v-model="f.key"
                      type="text"
                      placeholder="Label"
                      class="w-2/5 bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20 placeholder-neutral-700"
                    />
                    <input
                      v-model="f.value"
                      type="text"
                      placeholder="Valor"
                      class="flex-1 bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20 placeholder-neutral-700"
                    />
                    <button
                      type="button"
                      @click="removeField(i)"
                      class="p-1 text-neutral-600 hover:text-red-400 transition-colors shrink-0"
                    >
                      <Icon icon="solar:close-circle-bold-duotone" class="text-sm" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Footer fixo -->
            <div class="px-8 py-6 shrink-0 space-y-3">
              <p v-if="formError" class="text-xs font-mono text-red-400">{{ formError }}</p>
              <div class="flex gap-3">
                <button type="button" @click="modal = false" class="flex-1 py-3 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors">
                  Cancelar
                </button>
                <button type="submit" :disabled="formLoading" class="btn-primary flex-1 disabled:opacity-50">
                  <div class="corner-tl"></div>
                  <div class="corner-br"></div>
                  <span class="text-white text-xs font-mono uppercase tracking-wider">
                    {{ formLoading ? 'Salvando...' : 'Salvar' }}
                  </span>
                </button>
              </div>
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
