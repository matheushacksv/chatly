<script setup lang="ts">
import { Icon } from '@iconify/vue'

useHead({ title: 'Editar automação' })

const route = useRoute()
const api = useApi()
const automationId = Number(route.params.id)

interface Step {
  order?: number
  action_type: string
  config: Record<string, any>
  id?: number
  then_steps?: Step[]
  else_steps?: Step[]
}
interface Automation {
  id: number
  name: string
  trigger_type: string
  trigger_filters: Record<string, any>
  is_active: boolean
  steps: Step[]
}
interface TriggerMeta { type: string; label: string }
interface ActionMeta { type: string; label: string; fields: any[] }

const form = reactive<Automation>({
  id: 0, name: '', trigger_type: '', trigger_filters: {}, is_active: false, steps: [],
})

const triggers = ref<TriggerMeta[]>([])
const actions = ref<ActionMeta[]>([])
const templates = ref<any[]>([])
const labels = ref<any[]>([])
const members = ref<any[]>([])
const instances = ref<any[]>([])
const automationsList = ref<any[]>([])

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const successMsg = ref('')

const fetchAll = async () => {
  try {
    const [auto, trig, acts, tpls, lbls, mbrs, insts, autos] = await Promise.all([
      api<Automation>(`/api/automations/${automationId}/`),
      api<TriggerMeta[]>('/api/automations/triggers/'),
      api<ActionMeta[]>('/api/automations/actions/'),
      api<any[]>('/api/templates/').catch(() => []),
      api<any[]>('/api/labels/').catch(() => []),
      api<any[]>('/api/org/members').catch(() => []),
      api<any[]>('/api/integrations/whatsapp/').catch(() => []),
      api<any[]>('/api/automations/').catch(() => []),
    ])
    Object.assign(form, auto)
    triggers.value = trig
    actions.value = acts
    templates.value = tpls
    labels.value = lbls
    members.value = mbrs
    instances.value = insts
    // ação "Iniciar outra automação" só mira automações com gatilho "Iniciada por automação"
    automationsList.value = autos.filter(
      (a: any) => a.id !== automationId && a.trigger_type === 'automation.chained',
    )
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao carregar'
  } finally {
    loading.value = false
  }
}

const addStep = () => {
  form.steps.push({
    action_type: actions.value.find(a => a.type !== 'condition')?.type ?? 'send_message',
    config: {},
    then_steps: [],
    else_steps: [],
  })
}

const removeStep = (idx: number) => {
  form.steps.splice(idx, 1)
}

const move = (idx: number, dir: -1 | 1) => {
  const t = idx + dir
  if (t < 0 || t >= form.steps.length) return
  const tmp = form.steps[idx]
  form.steps[idx] = form.steps[t]
  form.steps[t] = tmp
}

// achata a árvore para o payload da API (order é reatribuído no backend)
const serializeStep = (s: Step): any => ({
  action_type: s.action_type,
  config: s.config,
  then_steps: (s.then_steps || []).map(serializeStep),
  else_steps: (s.else_steps || []).map(serializeStep),
})

// valida variações de mensagem antes de enviar (peso ≥ 1 e texto não-vazio)
const validateSteps = (steps: Step[]): string => {
  for (const s of steps) {
    const vs = s.action_type === 'send_message' ? (s.config?.variants || []) : []
    if (vs.length) {
      if (vs.some((v: any) => !String(v.text || '').trim()))
        return 'Há variação de mensagem com texto vazio.'
      if (vs.some((v: any) => !(Number(v.weight) >= 1)))
        return 'Cada variação precisa de um peso (%) ≥ 1.'
    }
    const bad = validateSteps(s.then_steps || []) || validateSteps(s.else_steps || [])
    if (bad) return bad
  }
  return ''
}

const save = async () => {
  const invalid = validateSteps(form.steps)
  if (invalid) { error.value = invalid; return }
  saving.value = true
  error.value = ''
  successMsg.value = ''
  try {
    await api(`/api/automations/${automationId}/`, {
      method: 'PATCH',
      body: {
        name: form.name,
        trigger_type: form.trigger_type,
        trigger_filters: form.trigger_filters,
        is_active: form.is_active,
        steps: form.steps.map(serializeStep),
      },
    })
    successMsg.value = 'Salvo'
    setTimeout(() => (successMsg.value = ''), 2000)
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao salvar'
  } finally {
    saving.value = false
  }
}

onMounted(fetchAll)
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 md:px-8 py-8">
    <div class="mb-6 flex items-center gap-3">
      <NuxtLink to="/automations" class="text-neutral-500 hover:text-neutral-300">
        <Icon icon="solar:arrow-left-bold-duotone" class="text-lg" />
      </NuxtLink>
      <div class="flex-1">
        <p class="field-label mb-0.5">Automação</p>
        <h1 class="text-xl font-medium text-white tracking-tight">{{ form.name || '...' }}</h1>
      </div>
      <NuxtLink :to="`/automations/${automationId}/runs`" class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 hover:text-neutral-300 px-3 py-2 border border-white/10">
        Histórico
      </NuxtLink>
    </div>

    <p v-if="error" class="text-xs font-mono text-red-400 mb-3">{{ error }}</p>

    <div v-if="loading" class="space-y-2">
      <div v-for="i in 5" :key="i" class="h-14 bg-white/5 animate-pulse"></div>
    </div>

    <div v-else class="space-y-5">
      <!-- Geral -->
      <div class="bg-surface border border-white/5 px-5 py-4 space-y-3">
        <div>
          <label class="field-label">Nome</label>
          <input
            v-model="form.name"
            type="text"
            class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
          />
        </div>

        <div>
          <label class="field-label">Gatilho</label>
          <select
            v-model="form.trigger_type"
            class="w-full bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 outline-none focus:border-white/20"
          >
            <option v-for="t in triggers" :key="t.type" :value="t.type">{{ t.label }}</option>
          </select>
        </div>

        <label class="flex items-center gap-2 cursor-pointer pt-2">
          <input v-model="form.is_active" type="checkbox" class="accent-accent" />
          <span class="text-xs font-mono text-neutral-300 uppercase tracking-widest">Ativa</span>
        </label>
      </div>

      <!-- Steps -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <p class="field-label mb-0">Passos ({{ form.steps.length }})</p>
          <button
            @click="addStep"
            class="text-[10px] font-mono uppercase tracking-widest text-accent hover:text-accent/80 px-3 py-1.5 border border-accent/30"
          >
            + Adicionar
          </button>
        </div>

        <div v-if="form.steps.length === 0" class="border border-white/5 px-5 py-8 text-center">
          <p class="text-xs font-mono text-neutral-700">Nenhum passo. Adicione uma ação.</p>
        </div>

        <div v-else class="space-y-2">
          <AutomationsStepEditor
            v-for="(step, idx) in form.steps"
            :key="idx"
            :step="step"
            :index="idx"
            :actions="actions"
            :templates="templates"
            :labels="labels"
            :members="members"
            :instances="instances"
            :automations="automationsList"
            @remove="removeStep(idx)"
            @move-up="move(idx, -1)"
            @move-down="move(idx, 1)"
          />
        </div>
      </div>

      <!-- Save -->
      <div class="flex items-center justify-end gap-3 pt-2">
        <span v-if="successMsg" class="text-[10px] font-mono uppercase tracking-widest text-accent">{{ successMsg }}</span>
        <button
          @click="save"
          :disabled="saving"
          class="btn-primary !w-auto px-6 py-3 disabled:opacity-40"
        >
          <div class="corner-tl"></div>
          <div class="corner-br"></div>
          <span class="text-white text-xs font-mono uppercase tracking-wider">{{ saving ? '...' : 'Salvar' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
