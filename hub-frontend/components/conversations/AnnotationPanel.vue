<script setup lang="ts">
import { Icon } from '@iconify/vue'

const props = defineProps<{
  contactId: number
  contactName: string
}>()

const emit = defineEmits<{ close: [] }>()

const api = useApi()

const annotations = ref<any[]>([])
const loading = ref(true)
const creating = ref(false)
const newContent = ref('')
const editingId = ref<number | null>(null)
const editContent = ref('')
const saving = ref(false)

const pinned   = computed(() => annotations.value.filter(a => a.pinned))
const unpinned = computed(() => annotations.value.filter(a => !a.pinned))

const fetchAnnotations = async () => {
  loading.value = true
  try {
    annotations.value = await api<any[]>(`/api/contacts/${props.contactId}/annotations`)
  } catch {
    annotations.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.contactId, () => fetchAnnotations(), { immediate: true })

const createAnnotation = async () => {
  if (!newContent.value.trim() || saving.value) return
  saving.value = true
  try {
    const ann = await api<any>(`/api/contacts/${props.contactId}/annotations`, {
      method: 'POST',
      body: { content: newContent.value.trim(), pinned: false },
    })
    annotations.value.unshift(ann)
    newContent.value = ''
    creating.value = false
  } catch {}
  finally { saving.value = false }
}

const togglePin = async (ann: any) => {
  try {
    const updated = await api<any>(
      `/api/contacts/${props.contactId}/annotations/${ann.id}`,
      { method: 'PATCH', body: { pinned: !ann.pinned } }
    )
    const idx = annotations.value.findIndex(a => a.id === ann.id)
    if (idx !== -1) annotations.value[idx] = updated
    // Re-sort: pinadas primeiro, depois por data
    annotations.value.sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  } catch {}
}

const startEdit = (ann: any) => {
  editingId.value = ann.id
  editContent.value = ann.content
}

const cancelEdit = () => {
  editingId.value = null
  editContent.value = ''
}

const saveEdit = async () => {
  if (!editContent.value.trim() || saving.value) return
  saving.value = true
  try {
    const updated = await api<any>(
      `/api/contacts/${props.contactId}/annotations/${editingId.value}`,
      { method: 'PATCH', body: { content: editContent.value.trim() } }
    )
    const idx = annotations.value.findIndex(a => a.id === updated.id)
    if (idx !== -1) annotations.value[idx] = updated
    editingId.value = null
    editContent.value = ''
  } catch {}
  finally { saving.value = false }
}

const deleteAnnotation = async (id: number) => {
  try {
    await api(`/api/contacts/${props.contactId}/annotations/${id}`, { method: 'DELETE' })
    annotations.value = annotations.value.filter(a => a.id !== id)
  } catch {}
}

const cancelCreate = () => {
  creating.value = false
  newContent.value = ''
}

const formatDate = (dt: string) => {
  const d = new Date(dt)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60_000) return 'agora'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h`
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}
</script>

<template>
  <div class="flex flex-col h-full bg-surface border-l border-white/10">

    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3.5 border-b border-white/5 shrink-0">
      <div>
        <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500">Anotações</p>
        <p class="text-xs font-medium text-white truncate max-w-[180px]">{{ contactName }}</p>
      </div>
      <button
        @click="emit('close')"
        class="p-1 text-neutral-500 hover:text-white transition-colors"
        title="Fechar"
      >
        <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
      </button>
    </div>

    <!-- Corpo scrollável -->
    <div class="flex-1 overflow-y-auto">

      <!-- Skeleton -->
      <div v-if="loading" class="p-4 space-y-3">
        <div v-for="i in 3" :key="i" class="animate-pulse space-y-2">
          <div class="h-3 bg-white/5 rounded w-full"></div>
          <div class="h-3 bg-white/5 rounded w-4/5"></div>
          <div class="h-2 bg-white/5 rounded w-1/3 mt-1"></div>
        </div>
      </div>

      <template v-else>

        <!-- Empty state -->
        <div
          v-if="annotations.length === 0"
          class="flex flex-col items-center justify-center h-48 text-center px-6"
        >
          <Icon icon="solar:notebook-bold-duotone" class="text-4xl text-white/10 mb-3" />
          <p class="text-xs font-mono text-neutral-700">Nenhuma anotação</p>
          <p class="text-[10px] font-mono text-neutral-700 mt-1">Clique em + Nova para começar</p>
        </div>

        <div v-else class="p-3 space-y-4">

          <!-- Seção: Pinadas -->
          <div v-if="pinned.length">
            <p class="field-label mb-2 flex items-center gap-1.5">
              <Icon icon="solar:pin-bold-duotone" class="text-accent text-xs" />
              Pinadas
            </p>
            <div class="space-y-2">
              <div
                v-for="ann in pinned"
                :key="ann.id"
                class="border border-accent/20 bg-accent/5 px-3 py-2.5"
              >
                <!-- Modo edição -->
                <template v-if="editingId === ann.id">
                  <textarea
                    v-model="editContent"
                    rows="3"
                    class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20 resize-none placeholder-neutral-700"
                    @keydown.ctrl.enter="saveEdit"
                  ></textarea>
                  <div class="flex items-center gap-2 mt-2">
                    <button
                      @click="saveEdit"
                      :disabled="saving"
                      class="text-[10px] font-mono text-accent hover:text-orange-300 transition-colors disabled:opacity-50"
                    >
                      {{ saving ? 'Salvando...' : 'Salvar' }}
                    </button>
                    <button
                      @click="cancelEdit"
                      class="text-[10px] font-mono text-neutral-500 hover:text-white transition-colors"
                    >
                      Cancelar
                    </button>
                  </div>
                </template>

                <!-- Modo leitura -->
                <template v-else>
                  <p class="text-xs text-white whitespace-pre-wrap leading-relaxed mb-2">{{ ann.content }}</p>
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5 min-w-0">
                      <span class="text-[10px] font-mono text-neutral-600 shrink-0">{{ formatDate(ann.created_at) }}</span>
                      <span v-if="ann.created_by_name" class="text-[10px] font-mono text-neutral-700 truncate">· {{ ann.created_by_name }}</span>
                    </div>
                    <div class="flex items-center gap-0.5 shrink-0">
                      <button @click="togglePin(ann)" class="p-1 text-accent hover:text-orange-300 transition-colors" title="Despinar">
                        <Icon icon="solar:pin-bold-duotone" class="text-xs" />
                      </button>
                      <button @click="startEdit(ann)" class="p-1 text-neutral-600 hover:text-neutral-300 transition-colors" title="Editar">
                        <Icon icon="solar:pen-bold-duotone" class="text-xs" />
                      </button>
                      <button @click="deleteAnnotation(ann.id)" class="p-1 text-neutral-600 hover:text-red-400 transition-colors" title="Remover">
                        <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-xs" />
                      </button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- Seção: Outras -->
          <div v-if="unpinned.length">
            <p class="field-label mb-2">Anotações</p>
            <div class="space-y-2">
              <div
                v-for="ann in unpinned"
                :key="ann.id"
                class="border border-white/5 bg-canvas px-3 py-2.5"
              >
                <!-- Modo edição -->
                <template v-if="editingId === ann.id">
                  <textarea
                    v-model="editContent"
                    rows="3"
                    class="w-full bg-surface border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20 resize-none placeholder-neutral-700"
                    @keydown.ctrl.enter="saveEdit"
                  ></textarea>
                  <div class="flex items-center gap-2 mt-2">
                    <button
                      @click="saveEdit"
                      :disabled="saving"
                      class="text-[10px] font-mono text-accent hover:text-orange-300 transition-colors disabled:opacity-50"
                    >
                      {{ saving ? 'Salvando...' : 'Salvar' }}
                    </button>
                    <button
                      @click="cancelEdit"
                      class="text-[10px] font-mono text-neutral-500 hover:text-white transition-colors"
                    >
                      Cancelar
                    </button>
                  </div>
                </template>

                <!-- Modo leitura -->
                <template v-else>
                  <p class="text-xs text-white whitespace-pre-wrap leading-relaxed mb-2">{{ ann.content }}</p>
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5 min-w-0">
                      <span class="text-[10px] font-mono text-neutral-600 shrink-0">{{ formatDate(ann.created_at) }}</span>
                      <span v-if="ann.created_by_name" class="text-[10px] font-mono text-neutral-700 truncate">· {{ ann.created_by_name }}</span>
                    </div>
                    <div class="flex items-center gap-0.5 shrink-0">
                      <button @click="togglePin(ann)" class="p-1 text-neutral-600 hover:text-accent transition-colors" title="Pinar">
                        <Icon icon="solar:pin-linear" class="text-xs" />
                      </button>
                      <button @click="startEdit(ann)" class="p-1 text-neutral-600 hover:text-neutral-300 transition-colors" title="Editar">
                        <Icon icon="solar:pen-bold-duotone" class="text-xs" />
                      </button>
                      <button @click="deleteAnnotation(ann.id)" class="p-1 text-neutral-600 hover:text-red-400 transition-colors" title="Remover">
                        <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-xs" />
                      </button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>

        </div>
      </template>
    </div>

    <!-- Footer: nova anotação -->
    <div class="border-t border-white/5 shrink-0">
      <!-- Form de criação -->
      <div v-if="creating" class="p-3">
        <textarea
          v-model="newContent"
          rows="3"
          placeholder="Escreva uma anotação..."
          autofocus
          class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20 resize-none placeholder-neutral-700 mb-2"
          @keydown.ctrl.enter="createAnnotation"
          @keydown.escape="cancelCreate"
        ></textarea>
        <div class="flex items-center gap-2">
          <button
            @click="createAnnotation"
            :disabled="!newContent.trim() || saving"
            class="px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-accent/30 text-accent hover:bg-accent/5 transition-colors disabled:opacity-40"
          >
            {{ saving ? 'Salvando...' : 'Salvar' }}
          </button>
          <button
            @click="cancelCreate"
            class="px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-white/10 text-neutral-400 hover:border-white/20 hover:text-white transition-colors"
          >
            Cancelar
          </button>
          <span class="text-[9px] font-mono text-neutral-700 ml-auto">Ctrl+Enter</span>
        </div>
      </div>

      <!-- Botão de abrir form -->
      <button
        v-else
        @click="creating = true"
        class="w-full px-4 py-3 flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-neutral-500 hover:text-accent hover:bg-accent/5 transition-colors"
      >
        <Icon icon="solar:add-circle-bold-duotone" class="text-sm" />
        Nova anotação
      </button>
    </div>

  </div>
</template>
