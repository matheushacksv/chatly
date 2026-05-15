<script setup lang="ts">
import { Icon } from '@iconify/vue'

interface FieldMeta {
  key: string
  label: string
  type: string
  required?: boolean
  options?: { value: string; label: string }[]
}

interface ActionMeta {
  type: string
  label: string
  fields: FieldMeta[]
}

const props = defineProps<{
  step: { order: number; action_type: string; config: Record<string, any> }
  index: number
  actions: ActionMeta[]
  templates: any[]
  labels: any[]
  members: any[]
  instances: any[]
}>()

const emit = defineEmits<{
  remove: []
  moveUp: []
  moveDown: []
}>()

const currentAction = computed(() => props.actions.find(a => a.type === props.step.action_type))

const api = useApi()
const pipelines = useState<any[]>('pipedrive-pipelines', () => [])
const pipelinesFetched = useState<boolean>('pipedrive-pipelines-fetched', () => false)

onMounted(async () => {
  if (pipelinesFetched.value) return
  const needs = props.actions.some(a => a.fields.some(f => f.type === 'pipedrive_stage_select'))
  if (!needs) return
  pipelinesFetched.value = true
  try {
    pipelines.value = await api<any[]>('/api/org/integrations/pipedrive/pipelines')
  } catch {}
})

const onActionChange = () => {
  // resetar config ao mudar tipo
  props.step.config = {}
}

const renderJson = (val: any) => {
  if (val === undefined || val === null) return ''
  if (typeof val === 'string') return val
  try { return JSON.stringify(val, null, 2) } catch { return String(val) }
}

const parseJson = (raw: string, key: string) => {
  if (!raw.trim()) {
    props.step.config[key] = {}
    return
  }
  try {
    props.step.config[key] = JSON.parse(raw)
  } catch {
    props.step.config[key] = raw
  }
}
</script>

<template>
  <div class="bg-surface border border-white/5">
    <div class="flex items-center justify-between px-4 py-2.5 border-b border-white/5">
      <div class="flex items-center gap-2">
        <span class="text-[10px] font-mono text-neutral-600 uppercase tracking-widest">#{{ index + 1 }}</span>
        <select
          v-model="props.step.action_type"
          @change="onActionChange"
          class="bg-canvas border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20"
        >
          <option v-for="a in actions" :key="a.type" :value="a.type">{{ a.label }}</option>
        </select>
      </div>
      <div class="flex items-center gap-1">
        <button @click="emit('moveUp')" class="p-1 text-neutral-600 hover:text-neutral-300 transition-colors" title="Subir">
          <Icon icon="solar:alt-arrow-up-bold-duotone" class="text-sm" />
        </button>
        <button @click="emit('moveDown')" class="p-1 text-neutral-600 hover:text-neutral-300 transition-colors" title="Descer">
          <Icon icon="solar:alt-arrow-down-bold-duotone" class="text-sm" />
        </button>
        <button @click="emit('remove')" class="p-1 text-neutral-600 hover:text-red-400 transition-colors" title="Remover">
          <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-sm" />
        </button>
      </div>
    </div>

    <div v-if="currentAction" class="px-4 py-3 space-y-3">
      <div v-if="currentAction.fields.length === 0" class="text-[10px] font-mono text-neutral-700 uppercase tracking-widest">
        Sem parâmetros
      </div>

      <div v-for="field in currentAction.fields" :key="field.key">
        <label class="field-label">
          {{ field.label }}
          <span v-if="field.required" class="text-red-400">*</span>
        </label>

        <!-- text -->
        <input
          v-if="field.type === 'text'"
          v-model="props.step.config[field.key]"
          type="text"
          class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
        />

        <!-- number -->
        <input
          v-else-if="field.type === 'number'"
          v-model.number="props.step.config[field.key]"
          type="number"
          class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
        />

        <!-- textarea -->
        <textarea
          v-else-if="field.type === 'textarea'"
          v-model="props.step.config[field.key]"
          rows="3"
          class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20 resize-y"
          placeholder="Use {{contact.name}}, {{conversation.id}}, {{message.content}}"
        ></textarea>

        <!-- boolean -->
        <label v-else-if="field.type === 'boolean'" class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="props.step.config[field.key]"
            type="checkbox"
            class="accent-accent"
          />
          <span class="text-xs font-mono text-neutral-400">Sim / Não</span>
        </label>

        <!-- select -->
        <select
          v-else-if="field.type === 'select'"
          v-model="props.step.config[field.key]"
          class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
        >
          <option value="">—</option>
          <option v-for="opt in field.options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>

        <!-- template select -->
        <select
          v-else-if="field.type === 'template_select'"
          v-model="props.step.config[field.key]"
          class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
        >
          <option value="">—</option>
          <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.title || t.name }}</option>
        </select>

        <!-- label select -->
        <select
          v-else-if="field.type === 'label_select'"
          v-model="props.step.config[field.key]"
          class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
        >
          <option value="">—</option>
          <option v-for="l in labels" :key="l.id" :value="l.id">{{ l.name }}</option>
        </select>

        <!-- instance select -->
        <select
          v-else-if="field.type === 'instance_select'"
          v-model="props.step.config[field.key]"
          class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
        >
          <option value="">—</option>
          <option v-for="i in instances" :key="i.id" :value="i.id">{{ i.name || i.instance_name }}</option>
        </select>

        <!-- user select -->
        <select
          v-else-if="field.type === 'user_select'"
          v-model="props.step.config[field.key]"
          class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
        >
          <option value="">—</option>
          <option v-for="m in members" :key="m.id || m.user_id" :value="m.id || m.user_id">
            {{ m.name || m.email || m.user_email }}
          </option>
        </select>

        <!-- pipedrive stage select -->
        <select
          v-else-if="field.type === 'pipedrive_stage_select'"
          v-model.number="props.step.config[field.key]"
          class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
        >
          <option :value="undefined">—</option>
          <optgroup v-for="p in pipelines" :key="p.id" :label="p.name">
            <option v-for="s in p.stages" :key="s.id" :value="s.id">{{ s.name }}</option>
          </optgroup>
        </select>

        <!-- json -->
        <textarea
          v-else-if="field.type === 'json'"
          :value="renderJson(props.step.config[field.key])"
          @input="(e: any) => parseJson(e.target.value, field.key)"
          rows="3"
          class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20 resize-y"
          placeholder='{"Content-Type": "application/json"}'
        ></textarea>
      </div>
    </div>
  </div>
</template>
