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

interface Step {
  order?: number
  action_type: string
  config: Record<string, any>
  then_steps?: Step[]
  else_steps?: Step[]
}

const props = defineProps<{
  step: Step
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
const isCondition = computed(() => props.step.action_type === 'condition')

const api = useApi()
const pipelines = useState<any[]>('pipedrive-pipelines', () => [])
const pipelinesFetched = useState<boolean>('pipedrive-pipelines-fetched', () => false)

onMounted(async () => {
  if (isCondition.value) ensureBranches()
  if (pipelinesFetched.value) return
  const needs = props.actions.some(a => a.fields.some(f => f.type === 'pipedrive_stage_select'))
  if (!needs) return
  pipelinesFetched.value = true
  try {
    pipelines.value = await api<any[]>('/api/org/integrations/pipedrive/pipelines')
  } catch {}
})

const ensureBranches = () => {
  if (!props.step.then_steps) props.step.then_steps = []
  if (!props.step.else_steps) props.step.else_steps = []
  if (!props.step.config.logic) props.step.config.logic = { combinator: 'AND', rules: [] }
}

const newStep = (): Step => ({
  action_type: props.actions.find(a => a.type !== 'condition')?.type ?? 'send_message',
  config: {},
  then_steps: [],
  else_steps: [],
})

const onActionChange = () => {
  // resetar config ao mudar tipo
  props.step.config = {}
  if (isCondition.value) ensureBranches()
}

const addChild = (branch: 'then' | 'else') => {
  ensureBranches()
  const arr = branch === 'then' ? props.step.then_steps! : props.step.else_steps!
  arr.push(newStep())
}

const removeChild = (arr: Step[], idx: number) => {
  arr.splice(idx, 1)
}

const moveChild = (arr: Step[], idx: number, dir: -1 | 1) => {
  const t = idx + dir
  if (t < 0 || t >= arr.length) return
  const tmp = arr[idx]
  arr[idx] = arr[t]
  arr[t] = tmp
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

    <!-- CONDIÇÃO: builder + ramos Então/Senão -->
    <div v-if="isCondition" class="px-4 py-3 space-y-4">
      <AutomationsConditionBuilder :logic="props.step.config.logic" />

      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase tracking-widest text-accent">Então</span>
          <button
            @click="addChild('then')"
            class="text-[10px] font-mono uppercase tracking-widest text-accent hover:text-accent/80 px-2.5 py-1 border border-accent/30"
          >+ Ação</button>
        </div>
        <div class="border-l-2 border-accent/30 pl-3 space-y-2">
          <p v-if="!props.step.then_steps || props.step.then_steps.length === 0" class="text-[10px] font-mono text-neutral-700 uppercase tracking-widest">
            Vazio
          </p>
          <AutomationsStepEditor
            v-for="(child, ci) in props.step.then_steps"
            :key="`then-${ci}`"
            :step="child"
            :index="ci"
            :actions="actions"
            :templates="templates"
            :labels="labels"
            :members="members"
            :instances="instances"
            @remove="removeChild(props.step.then_steps!, ci)"
            @move-up="moveChild(props.step.then_steps!, ci, -1)"
            @move-down="moveChild(props.step.then_steps!, ci, 1)"
          />
        </div>
      </div>

      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase tracking-widest text-neutral-400">Senão</span>
          <button
            @click="addChild('else')"
            class="text-[10px] font-mono uppercase tracking-widest text-neutral-400 hover:text-neutral-200 px-2.5 py-1 border border-white/15"
          >+ Ação</button>
        </div>
        <div class="border-l-2 border-white/15 pl-3 space-y-2">
          <p v-if="!props.step.else_steps || props.step.else_steps.length === 0" class="text-[10px] font-mono text-neutral-700 uppercase tracking-widest">
            Vazio
          </p>
          <AutomationsStepEditor
            v-for="(child, ci) in props.step.else_steps"
            :key="`else-${ci}`"
            :step="child"
            :index="ci"
            :actions="actions"
            :templates="templates"
            :labels="labels"
            :members="members"
            :instances="instances"
            @remove="removeChild(props.step.else_steps!, ci)"
            @move-up="moveChild(props.step.else_steps!, ci, -1)"
            @move-down="moveChild(props.step.else_steps!, ci, 1)"
          />
        </div>
      </div>
    </div>

    <!-- AÇÃO COMUM: campos dinâmicos -->
    <div v-else-if="currentAction" class="px-4 py-3 space-y-3">
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
