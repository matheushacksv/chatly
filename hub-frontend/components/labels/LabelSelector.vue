<script setup lang="ts">
import { Icon } from '@iconify/vue'

const props = defineProps<{
  entityType: 'contact' | 'conversation'
  entityId: number
  labels: Array<{ id: number; name: string; color: string }>
}>()

const emit = defineEmits<{ updated: [labels: Array<{ id: number; name: string; color: string }>] }>()

const api = useApi()
const labelsStore = useLabelsStore()

const open = ref(false)
const search = ref('')
const saving = ref(false)
const newName = ref('')
const newColor = ref('#6366f1')
const creating = ref(false)

const selectedIds = ref<Set<number>>(new Set(props.labels.map(l => l.id)))

watch(() => props.labels, (val) => {
  selectedIds.value = new Set(val.map(l => l.id))
})

watch(open, (val) => {
  if (val) {
    labelsStore.fetchLabels()
    selectedIds.value = new Set(props.labels.map(l => l.id))
    search.value = ''
  }
})

const filteredLabels = computed(() =>
  labelsStore.labels.filter(l => l.name.toLowerCase().includes(search.value.toLowerCase()))
)

const toggle = (id: number) => {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
}

const save = async () => {
  saving.value = true
  try {
    const endpoint = props.entityType === 'contact'
      ? `/api/contacts/${props.entityId}/labels`
      : `/api/conversations/${props.entityId}/labels`
    const updated = await api<any>(endpoint, {
      method: 'POST',
      body: { label_ids: [...selectedIds.value] },
    })
    emit('updated', updated.labels ?? [])
    open.value = false
  } catch {} finally {
    saving.value = false
  }
}

const createLabel = async () => {
  if (!newName.value.trim()) return
  creating.value = true
  try {
    const label = await labelsStore.createLabel({ name: newName.value.trim(), color: newColor.value })
    selectedIds.value = new Set([...selectedIds.value, label.id])
    newName.value = ''
  } catch {} finally {
    creating.value = false
  }
}

const PRESET_COLORS = [
  '#6366f1', '#3b82f6', '#22c55e', '#eab308',
  '#f97316', '#ef4444', '#ec4899', '#a855f7',
]

const el = ref<HTMLElement>()
onClickOutside(el, () => { open.value = false })
</script>

<template>
  <div ref="el" class="relative">
    <!-- Trigger -->
    <div
      class="flex items-center gap-1.5 flex-wrap cursor-pointer group"
      @click="open = !open"
    >
      <template v-if="labels.length > 0">
        <LabelsLabelBadge
          v-for="l in labels"
          :key="l.id"
          :name="l.name"
          :color="l.color"
        />
      </template>
      <span
        class="text-[10px] font-mono text-neutral-700 group-hover:text-neutral-400 transition-colors flex items-center gap-0.5"
      >
        <Icon icon="solar:tag-bold-duotone" class="text-xs" />
        {{ labels.length === 0 ? 'Adicionar etiqueta' : 'Editar' }}
      </span>
    </div>

    <!-- Dropdown -->
    <Transition name="drop">
      <div
        v-if="open"
        class="absolute left-0 top-full mt-1 z-50 w-64 bg-surface border border-white/10 shadow-xl"
      >
        <!-- Search -->
        <div class="px-3 pt-3 pb-2 border-b border-white/5">
          <input
            v-model="search"
            type="text"
            placeholder="Buscar etiqueta..."
            class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-1.5 outline-none focus:border-white/20 placeholder-neutral-700"
          />
        </div>

        <!-- Lista -->
        <div class="max-h-48 overflow-y-auto py-1">
          <div
            v-if="labelsStore.labels.length === 0"
            class="px-4 py-3 text-[11px] font-mono text-neutral-700"
          >
            Nenhuma etiqueta criada ainda.
          </div>
          <button
            v-for="label in filteredLabels"
            :key="label.id"
            type="button"
            @click="toggle(label.id)"
            class="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-white/5 transition-colors"
          >
            <div
              class="w-3.5 h-3.5 border shrink-0 flex items-center justify-center transition-colors"
              :style="selectedIds.has(label.id)
                ? `border-color: ${label.color}; background: ${label.color}`
                : `border-color: ${label.color}50`"
            >
              <Icon
                v-if="selectedIds.has(label.id)"
                icon="solar:check-bold"
                class="text-white text-[9px]"
              />
            </div>
            <span class="w-2 h-2 rounded-full shrink-0" :style="`background: ${label.color}`"></span>
            <span class="text-xs font-mono text-neutral-300 truncate">{{ label.name }}</span>
          </button>
        </div>

        <!-- Nova etiqueta -->
        <div class="border-t border-white/5 px-3 py-2.5">
          <p class="text-[9px] font-mono uppercase tracking-widest text-neutral-600 mb-2">Nova etiqueta</p>
          <div class="flex gap-2 mb-2">
            <input
              v-model="newName"
              type="text"
              placeholder="Nome..."
              @keydown.enter.prevent="createLabel"
              class="flex-1 bg-canvas border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20 placeholder-neutral-700"
            />
            <button
              type="button"
              @click="createLabel"
              :disabled="!newName.trim() || creating"
              class="px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-accent/30 text-accent hover:bg-accent/5 transition-colors disabled:opacity-40"
            >
              +
            </button>
          </div>
          <!-- Paleta de cores -->
          <div class="flex gap-1.5 flex-wrap">
            <button
              v-for="c in PRESET_COLORS"
              :key="c"
              type="button"
              @click="newColor = c"
              class="w-4 h-4 rounded-full border-2 transition-transform hover:scale-110"
              :style="`background: ${c}; border-color: ${newColor === c ? 'white' : c}`"
            />
          </div>
        </div>

        <!-- Ações -->
        <div class="border-t border-white/5 px-3 py-2.5 flex gap-2">
          <button
            type="button"
            @click="open = false"
            class="flex-1 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-white/10 text-neutral-400 hover:border-white/20 hover:text-white transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            @click="save"
            :disabled="saving"
            class="flex-1 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-accent/30 text-accent hover:bg-accent/5 transition-colors disabled:opacity-40"
          >
            {{ saving ? '...' : 'Salvar' }}
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.drop-enter-active, .drop-leave-active { transition: opacity 0.1s, transform 0.1s; }
.drop-enter-from, .drop-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
