<script setup lang="ts">
import { Icon } from '@iconify/vue'

const api = useApi()
const { confirm: confirmDialog } = useConfirm()

const templates = ref<any[]>([])
const loading = ref(true)
const modal = ref(false)
const editingTemplate = ref<any>(null)
const formLoading = ref(false)
const formError = ref('')

type MediaType = 'text' | 'image' | 'document' | 'audio' | 'sticker'

const form = reactive({
  title: '',
  shortcut: '',
  media_type: 'text' as MediaType,
  content: '',
})
const fileInput = ref<HTMLInputElement>()
const selectedFile = ref<File | null>(null)

// --- Biblioteca de figurinhas ---
const stickers = ref<any[]>([])
const stickersLoading = ref(false)
const selectedStickerUrl = ref<string | null>(null)
const selectedStickerMime = ref<string>('image/webp')

const fetchStickers = async () => {
  if (stickers.value.length > 0) return
  stickersLoading.value = true
  try {
    stickers.value = await api<any[]>('/api/conversations/stickers')
  } catch {}
  finally { stickersLoading.value = false }
}

const onTypeChange = (type: MediaType) => {
  form.media_type = type
  selectedFile.value = null
  selectedStickerUrl.value = null
  if (type === 'sticker') fetchStickers()
}

// ---

const search = ref('')

const filteredTemplates = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return templates.value
  return templates.value.filter(t =>
    t.title?.toLowerCase().includes(q) ||
    t.shortcut?.toLowerCase().includes(q) ||
    t.content?.toLowerCase().includes(q)
  )
})

const { page: tplPage, totalPages: tplTotalPages, paged: pagedTemplates, prev: tplPrev, next: tplNext, goTo: tplGoTo } = usePagination(filteredTemplates, 15)

const fetchTemplates = async () => {
  try {
    templates.value = await api<any[]>('/api/templates/')
  } catch {}
  finally { loading.value = false }
}

onMounted(fetchTemplates)

const typeConfig: Record<string, { icon: string; label: string; accept?: string }> = {
  text:     { icon: 'solar:text-bold-duotone',                     label: 'Texto' },
  image:    { icon: 'solar:gallery-bold-duotone',                  label: 'Imagem',    accept: 'image/*' },
  document: { icon: 'solar:file-text-bold-duotone',                label: 'Documento', accept: '.pdf,.doc,.docx,.xls,.xlsx,.txt' },
  audio:    { icon: 'solar:microphone-bold-duotone',               label: 'Áudio',     accept: 'audio/*' },
  sticker:  { icon: 'solar:sticker-smile-circle-2-bold-duotone',   label: 'Figurinha' },
}

const typeList: MediaType[] = ['text', 'image', 'document', 'audio', 'sticker']

const openCreate = () => {
  editingTemplate.value = null
  form.title = ''
  form.shortcut = ''
  form.media_type = 'text'
  form.content = ''
  selectedFile.value = null
  selectedStickerUrl.value = null
  formError.value = ''
  modal.value = true
}

const openEdit = (t: any) => {
  editingTemplate.value = t
  form.title = t.title
  form.shortcut = t.shortcut || ''
  form.media_type = t.media_type
  form.content = t.content || ''
  selectedFile.value = null
  selectedStickerUrl.value = null
  formError.value = ''
  modal.value = true
}

const onFileChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

const isMediaWithFile = (type: MediaType) => ['image', 'document', 'audio'].includes(type)
const hasCaption      = (type: MediaType) => ['image', 'document'].includes(type)

const saveTemplate = async () => {
  if (!form.title.trim()) { formError.value = 'Título obrigatório'; return }
  if (!editingTemplate.value) {
    if (form.media_type === 'sticker' && !selectedStickerUrl.value) {
      formError.value = 'Selecione uma figurinha'; return
    }
    if (isMediaWithFile(form.media_type) && !selectedFile.value) {
      formError.value = 'Selecione um arquivo'; return
    }
  }

  formLoading.value = true
  formError.value = ''

  try {
    if (editingTemplate.value) {
      // PATCH — apenas campos editáveis (sem re-upload)
      const updated = await api<any>(`/api/templates/${editingTemplate.value.id}`, {
        method: 'PATCH',
        body: { title: form.title, shortcut: form.shortcut, content: form.content },
      })
      const idx = templates.value.findIndex(t => t.id === updated.id)
      if (idx !== -1) templates.value[idx] = updated

    } else if (form.media_type === 'text') {
      const created = await api<any>('/api/templates/', {
        method: 'POST',
        body: { title: form.title, shortcut: form.shortcut, content: form.content },
      })
      templates.value.unshift(created)

    } else if (form.media_type === 'sticker') {
      // Busca o blob da figurinha selecionada e faz upload
      const resp = await fetch(selectedStickerUrl.value!)
      const blob = await resp.blob()
      const mime = blob.type || selectedStickerMime.value || 'image/webp'
      const ext  = mime.split('/')[1]?.split(';')[0] || 'webp'
      const file = new File([blob], `sticker.${ext}`, { type: mime })

      const fd = new FormData()
      fd.append('title', form.title)
      fd.append('shortcut', form.shortcut)
      fd.append('content', '')   // figurinha não tem legenda
      fd.append('media_type', 'sticker')
      fd.append('file', file)
      const created = await api<any>('/api/templates/media', { method: 'POST', body: fd })
      templates.value.unshift(created)

    } else {
      // image | document | audio
      const fd = new FormData()
      fd.append('title', form.title)
      fd.append('shortcut', form.shortcut)
      fd.append('content', form.content)
      fd.append('media_type', form.media_type)
      fd.append('file', selectedFile.value!)
      const created = await api<any>('/api/templates/media', { method: 'POST', body: fd })
      templates.value.unshift(created)
    }

    modal.value = false
  } catch (e: any) {
    formError.value = e?.data?.detail || 'Erro ao salvar'
  } finally {
    formLoading.value = false
  }
}

const deleteTemplate = async (t: any) => {
  if (!await confirmDialog(`Remover "${t.title}"?`, { title: 'Remover template' })) return
  try {
    await api(`/api/templates/${t.id}`, { method: 'DELETE' })
    templates.value = templates.value.filter(x => x.id !== t.id)
  } catch {}
}
</script>

<template>
  <div class="p-4 md:p-8 max-w-4xl">
    <!-- Header -->
    <div class="flex flex-wrap items-start justify-between gap-y-3 mb-8">
      <div>
        <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-1">Mensagens</p>
        <h1 class="text-2xl font-medium text-white tracking-tight">Templates</h1>
      </div>
      <button
        @click="openCreate"
        class="relative flex items-center gap-2 px-4 py-2 text-xs font-mono uppercase tracking-widest border border-neutral-800 text-neutral-300 hover:border-accent/60 hover:text-accent transition-all group"
      >
        <span class="absolute top-0 left-0 w-1.5 h-1.5 border-t border-l border-accent opacity-0 group-hover:opacity-100 transition-opacity"></span>
        <span class="absolute top-0 right-0 w-1.5 h-1.5 border-t border-r border-accent opacity-0 group-hover:opacity-100 transition-opacity"></span>
        <span class="absolute bottom-0 left-0 w-1.5 h-1.5 border-b border-l border-accent opacity-0 group-hover:opacity-100 transition-opacity"></span>
        <span class="absolute bottom-0 right-0 w-1.5 h-1.5 border-b border-r border-accent opacity-0 group-hover:opacity-100 transition-opacity"></span>
        <Icon icon="solar:add-circle-bold-duotone" class="text-base" />
        Novo template
      </button>
    </div>

    <!-- Busca -->
    <div v-if="!loading && templates.length > 0" class="flex items-center gap-2 px-4 py-2.5 bg-surface border border-white/5 focus-within:border-accent/30 transition-colors mb-4">
      <Icon icon="solar:magnifer-bold-duotone" class="text-sm text-neutral-600 shrink-0" />
      <input
        v-model="search"
        type="text"
        placeholder="Buscar por título, atalho ou conteúdo..."
        class="bg-transparent text-xs font-mono text-white outline-none placeholder-neutral-700 flex-1 min-w-0"
      />
      <button v-if="search" @click="search = ''" class="text-neutral-600 hover:text-neutral-400 transition-colors">
        <Icon icon="solar:close-circle-bold-duotone" class="text-sm" />
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 4" :key="i" class="h-20 bg-white/[0.02] border border-white/5 animate-pulse"></div>
    </div>

    <!-- Empty -->
    <div v-else-if="filteredTemplates.length === 0" class="flex flex-col items-center justify-center py-24 border border-white/5 bg-surface">
      <Icon icon="solar:document-text-bold-duotone" class="text-5xl text-white/10 mb-3" />
      <p class="text-sm font-mono text-neutral-700 mb-1">{{ search ? 'Nenhum resultado' : 'Nenhum template criado' }}</p>
      <p v-if="!search" class="text-xs font-mono text-neutral-800">Crie templates para agilizar o atendimento</p>
    </div>

    <!-- Lista -->
    <div v-else class="space-y-2">
      <div
        v-for="t in pagedTemplates"
        :key="t.id"
        class="flex items-center gap-4 px-5 py-4 bg-surface border border-white/5 hover:border-white/10 transition-colors group"
      >
        <!-- Preview figurinha -->
        <div v-if="t.media_type === 'sticker' && t.file_url" class="w-9 h-9 shrink-0">
          <img :src="t.file_url" class="w-full h-full object-contain" />
        </div>
        <!-- Ícone outros tipos -->
        <div v-else class="w-9 h-9 flex items-center justify-center border border-white/5 bg-canvas shrink-0">
          <Icon :icon="typeConfig[t.media_type]?.icon || 'solar:text-bold-duotone'" class="text-lg text-neutral-500" />
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-sm text-white font-medium">{{ t.title }}</span>
            <span v-if="t.shortcut" class="text-[9px] font-mono text-accent bg-accent/10 px-1.5 py-0.5 uppercase tracking-widest">/{{ t.shortcut }}</span>
            <span class="text-[9px] font-mono text-neutral-700 bg-white/5 px-1.5 py-0.5 uppercase tracking-widest">
              {{ typeConfig[t.media_type]?.label || t.media_type }}
            </span>
          </div>
          <p v-if="t.content" class="text-xs font-mono text-neutral-600 truncate">{{ t.content }}</p>
          <p v-else-if="t.file_url && t.media_type !== 'sticker'" class="text-xs font-mono text-neutral-700 truncate">
            {{ t.file_url.split('/').pop() }}
          </p>
        </div>

        <!-- Ações -->
        <div class="flex items-center gap-1 shrink-0">
          <button @click="openEdit(t)" class="p-2 text-neutral-400 hover:text-white transition-colors" title="Editar">
            <Icon icon="solar:pen-bold-duotone" class="text-sm" />
          </button>
          <button @click="deleteTemplate(t)" class="p-2 text-neutral-400 hover:text-red-400 transition-colors" title="Remover">
            <Icon icon="solar:trash-bin-2-bold-duotone" class="text-sm" />
          </button>
        </div>
      </div>
    </div>

    <AppPagination
      v-if="tplTotalPages > 1"
      :page="tplPage"
      :total-pages="tplTotalPages"
      @prev="tplPrev"
      @next="tplNext"
      @go-to="tplGoTo"
    />
  </div>

  <!-- Modal -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/70" @click="modal = false"></div>
        <div class="relative bg-surface border border-white/10 w-full max-w-lg max-h-[90vh] flex flex-col">

          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-white/5 shrink-0">
            <h2 class="text-sm font-mono uppercase tracking-widest text-white">
              {{ editingTemplate ? 'Editar template' : 'Novo template' }}
            </h2>
            <button @click="modal = false" class="text-neutral-400 hover:text-white transition-colors">
              <Icon icon="solar:close-circle-bold-duotone" class="text-lg" />
            </button>
          </div>

          <div class="px-6 py-5 space-y-4 overflow-y-auto flex-1">

            <!-- Tipo (só na criação) -->
            <div v-if="!editingTemplate">
              <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-2">Tipo</p>
              <div class="grid grid-cols-5 gap-2">
                <button
                  v-for="type in typeList"
                  :key="type"
                  @click="onTypeChange(type)"
                  class="flex flex-col items-center gap-1.5 py-3 border transition-colors text-[10px] font-mono uppercase tracking-widest"
                  :class="form.media_type === type
                    ? 'border-accent/50 text-accent bg-accent/5'
                    : 'border-white/5 text-neutral-500 hover:border-white/20 hover:text-neutral-400'"
                >
                  <Icon :icon="typeConfig[type].icon" class="text-lg" />
                  {{ typeConfig[type].label }}
                </button>
              </div>
            </div>

            <!-- Título -->
            <div>
              <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-1.5">Título</p>
              <input
                v-model="form.title"
                type="text"
                placeholder="Ex: Saudação inicial"
                class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-4 py-2.5 outline-none focus:border-accent/50 placeholder-neutral-700"
              />
            </div>

            <!-- Shortcut -->
            <div>
              <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-1.5">
                Atalho
                <span class="text-neutral-700 normal-case tracking-normal font-sans font-normal ml-1">(opcional — invocado com /atalho no chat)</span>
              </p>
              <div class="flex items-center border border-white/10 focus-within:border-accent/50 bg-canvas">
                <span class="px-3 text-neutral-600 font-mono text-sm select-none">/</span>
                <input
                  v-model="form.shortcut"
                  type="text"
                  placeholder="ola"
                  class="flex-1 bg-transparent text-sm text-white font-mono py-2.5 pr-4 outline-none placeholder-neutral-700"
                />
              </div>
            </div>

            <!-- TEXTO: campo mensagem -->
            <div v-if="form.media_type === 'text' || editingTemplate?.media_type === 'text'">
              <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-1.5">Mensagem</p>
              <textarea
                v-model="form.content"
                placeholder="Texto da mensagem..."
                rows="4"
                class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-4 py-2.5 outline-none focus:border-accent/50 placeholder-neutral-700 resize-none"
              ></textarea>
            </div>

            <!-- IMAGEM / DOCUMENTO / ÁUDIO: upload (criação) -->
            <template v-else-if="isMediaWithFile(form.media_type) && !editingTemplate">
              <!-- Legenda apenas para imagem e documento -->
              <div v-if="hasCaption(form.media_type)">
                <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-1.5">
                  Legenda
                  <span class="text-neutral-700 normal-case tracking-normal font-sans font-normal ml-1">(opcional)</span>
                </p>
                <input
                  v-model="form.content"
                  type="text"
                  placeholder="Legenda da mídia..."
                  class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-4 py-2.5 outline-none focus:border-accent/50 placeholder-neutral-700"
                />
              </div>
              <div>
                <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-1.5">
                  {{ typeConfig[form.media_type].label }}
                </p>
                <input ref="fileInput" type="file" class="hidden" :accept="typeConfig[form.media_type].accept" @change="onFileChange" />
                <button
                  @click="fileInput?.click()"
                  class="w-full flex items-center gap-3 px-4 py-3 border border-dashed transition-colors"
                  :class="selectedFile
                    ? 'border-accent/40 text-accent'
                    : 'border-white/10 text-neutral-500 hover:border-white/20 hover:text-neutral-400'"
                >
                  <Icon icon="solar:upload-minimalistic-bold-duotone" class="text-lg shrink-0" />
                  <span class="text-xs font-mono truncate">{{ selectedFile ? selectedFile.name : 'Clique para selecionar' }}</span>
                </button>
              </div>
            </template>

            <!-- FIGURINHA: biblioteca de stickers (criação) -->
            <template v-else-if="form.media_type === 'sticker' && !editingTemplate">
              <div>
                <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-2">Figurinha</p>

                <div v-if="stickersLoading" class="grid grid-cols-6 gap-2">
                  <div v-for="i in 6" :key="i" class="aspect-square bg-white/5 animate-pulse"></div>
                </div>

                <div v-else-if="stickers.length === 0" class="flex flex-col items-center py-8 border border-white/5 bg-canvas">
                  <Icon icon="solar:sticker-smile-circle-2-bold-duotone" class="text-3xl text-white/10 mb-2" />
                  <p class="text-xs font-mono text-neutral-700">Nenhuma figurinha na biblioteca</p>
                  <p class="text-[10px] font-mono text-neutral-800 mt-0.5">Salve figurinhas no chat primeiro</p>
                </div>

                <div v-else class="grid grid-cols-6 gap-2 max-h-48 overflow-y-auto">
                  <button
                    v-for="sticker in stickers"
                    :key="sticker.id"
                    @click="selectedStickerUrl = sticker.file_url; selectedStickerMime = 'image/webp'"
                    class="aspect-square p-1 border transition-colors"
                    :class="selectedStickerUrl === sticker.file_url
                      ? 'border-accent/60 bg-accent/5'
                      : 'border-white/5 bg-canvas hover:border-white/20'"
                  >
                    <img :src="sticker.file_url" :alt="sticker.name" class="w-full h-full object-contain" />
                  </button>
                </div>

                <!-- Figurinha selecionada -->
                <div v-if="selectedStickerUrl" class="mt-2 flex items-center gap-2 text-[10px] font-mono text-accent">
                  <Icon icon="solar:check-circle-bold-duotone" class="text-sm" />
                  Figurinha selecionada
                </div>
              </div>
            </template>

            <!-- Editar mídia/sticker: mostrar arquivo atual (sem re-upload) -->
            <template v-else-if="editingTemplate && editingTemplate.media_type !== 'text'">
              <!-- Legenda editável para imagem/doc/audio -->
              <div v-if="hasCaption(editingTemplate.media_type)">
                <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-1.5">Legenda</p>
                <input
                  v-model="form.content"
                  type="text"
                  placeholder="Legenda da mídia..."
                  class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-4 py-2.5 outline-none focus:border-accent/50 placeholder-neutral-700"
                />
              </div>
              <!-- Preview do arquivo atual -->
              <div class="flex items-center gap-3 px-3 py-2 bg-white/[0.02] border border-white/5">
                <img
                  v-if="editingTemplate.media_type === 'sticker'"
                  :src="editingTemplate.file_url"
                  class="w-10 h-10 object-contain shrink-0"
                />
                <Icon
                  v-else
                  :icon="typeConfig[editingTemplate.media_type]?.icon"
                  class="text-lg text-neutral-500 shrink-0"
                />
                <div class="min-w-0">
                  <p class="text-[10px] font-mono text-neutral-600 truncate">
                    {{ editingTemplate.media_type === 'sticker' ? 'Figurinha' : editingTemplate.file_url?.split('/').pop() }}
                  </p>
                  <p class="text-[9px] font-mono text-neutral-800">Arquivo não pode ser alterado após criação</p>
                </div>
              </div>
            </template>

            <!-- Erro -->
            <p v-if="formError" class="text-xs font-mono text-red-400">{{ formError }}</p>
          </div>

          <div class="flex justify-end gap-2 px-6 py-4 border-t border-white/5 shrink-0">
            <button
              @click="modal = false"
              class="px-4 py-2 text-xs font-mono uppercase tracking-widest border border-white/10 text-neutral-500 hover:border-white/20 hover:text-white transition-colors"
            >
              Cancelar
            </button>
            <button
              @click="saveTemplate"
              :disabled="formLoading"
              class="px-4 py-2 text-xs font-mono uppercase tracking-widest border border-accent/40 text-accent hover:bg-accent/10 transition-colors disabled:opacity-50"
            >
              {{ formLoading ? 'Salvando...' : editingTemplate ? 'Salvar' : 'Criar' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s }
.fade-enter-from, .fade-leave-to { opacity: 0 }
</style>
