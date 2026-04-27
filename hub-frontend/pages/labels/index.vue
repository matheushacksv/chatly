<script setup lang="ts">
import { Icon } from '@iconify/vue'

const labelsStore = useLabelsStore()
const { confirm: confirmDialog } = useConfirm()

const loading = ref(true)
const error = ref('')

// ---- Create ----
const createForm = reactive({ name: '', color: '#6366f1' })
const creating = ref(false)
const createError = ref('')

const PRESET_COLORS = [
  '#6366f1', '#3b82f6', '#22c55e', '#eab308',
  '#f97316', '#ef4444', '#ec4899', '#a855f7',
]

const createLabel = async () => {
  if (!createForm.name.trim()) return
  creating.value = true
  createError.value = ''
  try {
    await labelsStore.createLabel({ name: createForm.name.trim(), color: createForm.color })
    createForm.name = ''
    createForm.color = '#6366f1'
  } catch (e: any) {
    createError.value = e?.data?.detail || 'Erro ao criar etiqueta'
  } finally {
    creating.value = false
  }
}

// ---- Edit ----
const editingId = ref<number | null>(null)
const editForm = reactive({ name: '', color: '' })
const editLoading = ref(false)
const editError = ref('')

const startEdit = (label: any) => {
  editingId.value = label.id
  editForm.name = label.name
  editForm.color = label.color
  editError.value = ''
}

const cancelEdit = () => {
  editingId.value = null
}

const saveEdit = async () => {
  if (!editForm.name.trim() || !editingId.value) return
  editLoading.value = true
  editError.value = ''
  try {
    await labelsStore.updateLabel(editingId.value, { name: editForm.name.trim(), color: editForm.color })
    editingId.value = null
  } catch (e: any) {
    editError.value = e?.data?.detail || 'Erro ao salvar'
  } finally {
    editLoading.value = false
  }
}

// ---- Delete ----
const deleteLabel = async (label: any) => {
  if (!await confirmDialog(`Remover etiqueta "${label.name}"? Ela será removida de todos os contatos e conversas.`, { title: 'Remover etiqueta' })) return
  try {
    await labelsStore.deleteLabel(label.id)
  } catch {}
}

onMounted(async () => {
  await labelsStore.fetchLabels(true)
  loading.value = false
})
</script>

<template>
  <div class="max-w-2xl mx-auto px-4 md:px-8 py-8">
    <!-- Header -->
    <div class="mb-8">
      <p class="field-label mb-0.5">Organização</p>
      <h1 class="text-xl font-medium text-white tracking-tight">Etiquetas</h1>
      <p class="text-xs font-mono text-neutral-600 mt-1">Crie etiquetas para organizar contatos e conversas.</p>
    </div>

    <!-- Create form -->
    <div class="bg-surface border border-white/5 px-6 py-5 mb-6">
      <p class="field-label mb-4">Nova etiqueta</p>
      <div class="flex gap-3 items-end">
        <div class="flex-1">
          <label class="field-label">Nome</label>
          <div class="input-wrapper">
            <input
              v-model="createForm.name"
              type="text"
              placeholder="Ex: Lead quente"
              class="input-field"
              @keydown.enter.prevent="createLabel"
            />
          </div>
        </div>
        <button
          @click="createLabel"
          :disabled="!createForm.name.trim() || creating"
          class="btn-primary !w-auto px-6 py-3 disabled:opacity-40"
        >
          <div class="corner-tl"></div>
          <div class="corner-br"></div>
          <span class="text-white text-xs font-mono uppercase tracking-wider">
            {{ creating ? '...' : 'Criar' }}
          </span>
        </button>
      </div>

      <!-- Color palette -->
      <div class="mt-3">
        <label class="field-label mb-2">Cor</label>
        <div class="flex gap-2 flex-wrap">
          <button
            v-for="c in PRESET_COLORS"
            :key="c"
            type="button"
            @click="createForm.color = c"
            class="w-6 h-6 rounded-full border-2 transition-transform hover:scale-110"
            :style="`background: ${c}; border-color: ${createForm.color === c ? 'white' : c}`"
            :title="c"
          />
          <div
            class="w-6 h-6 rounded-full border border-white/20 flex items-center justify-center"
            :style="`background: ${createForm.color}`"
          ></div>
        </div>
      </div>

      <p v-if="createError" class="text-xs font-mono text-red-400 mt-3">{{ createError }}</p>
    </div>

    <!-- Labels list -->
    <div>
      <p class="field-label mb-3">Etiquetas criadas ({{ labelsStore.labels.length }})</p>

      <div v-if="loading" class="space-y-2">
        <div v-for="i in 4" :key="i" class="h-14 bg-white/5 animate-pulse"></div>
      </div>

      <div v-else-if="labelsStore.labels.length === 0" class="flex flex-col items-center justify-center py-16 border border-white/5 text-center">
        <Icon icon="solar:tag-bold-duotone" class="text-4xl text-white/10 mb-3" />
        <p class="text-xs font-mono text-neutral-700">Nenhuma etiqueta criada ainda.</p>
      </div>

      <div v-else class="space-y-px">
        <div
          v-for="label in labelsStore.labels"
          :key="label.id"
          class="bg-surface border border-white/5"
        >
          <!-- View mode -->
          <div v-if="editingId !== label.id" class="flex items-center justify-between px-5 py-3.5">
            <div class="flex items-center gap-3">
              <span
                class="w-3 h-3 rounded-full shrink-0"
                :style="`background: ${label.color}`"
              ></span>
              <span class="text-sm text-white font-mono">{{ label.name }}</span>
              <LabelsLabelBadge :name="label.name" :color="label.color" />
            </div>
            <div class="flex items-center gap-1">
              <button
                @click="startEdit(label)"
                class="p-1.5 text-neutral-600 hover:text-neutral-300 transition-colors"
                title="Editar"
              >
                <Icon icon="solar:pen-bold-duotone" class="text-sm" />
              </button>
              <button
                @click="deleteLabel(label)"
                class="p-1.5 text-neutral-600 hover:text-red-400 transition-colors"
                title="Remover"
              >
                <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-sm" />
              </button>
            </div>
          </div>

          <!-- Edit mode -->
          <div v-else class="px-5 py-3.5">
            <div class="flex gap-3 items-end mb-3">
              <div class="flex-1">
                <label class="field-label">Nome</label>
                <input
                  v-model="editForm.name"
                  type="text"
                  class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
                  @keydown.enter.prevent="saveEdit"
                  @keydown.escape="cancelEdit"
                />
              </div>
              <div class="flex gap-2 pb-2">
                <button
                  @click="saveEdit"
                  :disabled="editLoading"
                  class="px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-accent/30 text-accent hover:bg-accent/5 transition-colors disabled:opacity-40"
                >
                  {{ editLoading ? '...' : 'Salvar' }}
                </button>
                <button
                  @click="cancelEdit"
                  class="px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-white/10 text-neutral-400 hover:border-white/20 transition-colors"
                >
                  Cancelar
                </button>
              </div>
            </div>
            <!-- Color palette no edit -->
            <div class="flex gap-2 flex-wrap">
              <button
                v-for="c in PRESET_COLORS"
                :key="c"
                type="button"
                @click="editForm.color = c"
                class="w-5 h-5 rounded-full border-2 transition-transform hover:scale-110"
                :style="`background: ${c}; border-color: ${editForm.color === c ? 'white' : c}`"
              />
            </div>
            <p v-if="editError" class="text-xs font-mono text-red-400 mt-2">{{ editError }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
