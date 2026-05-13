<script setup lang="ts">
import { Icon } from '@iconify/vue'

useHead({ title: 'Automações' })

const api = useApi()
const { confirm: confirmDialog } = useConfirm()

interface Automation {
  id: number
  name: string
  trigger_type: string
  is_active: boolean
  steps_count: number
  created_at: string
  updated_at: string
}

interface TriggerMeta { type: string; label: string }

const automations = ref<Automation[]>([])
const triggers = ref<TriggerMeta[]>([])
const loading = ref(true)
const error = ref('')

const triggerLabel = (t: string) => triggers.value.find(x => x.type === t)?.label ?? t

const fetchAll = async () => {
  loading.value = true
  try {
    const [list, trig] = await Promise.all([
      api<Automation[]>('/api/automations/'),
      api<TriggerMeta[]>('/api/automations/triggers/'),
    ])
    automations.value = list
    triggers.value = trig
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao carregar automações'
  } finally {
    loading.value = false
  }
}

const toggle = async (a: Automation) => {
  try {
    const updated = await api<Automation>(`/api/automations/${a.id}/toggle/`, {
      method: 'POST',
      body: { is_active: !a.is_active },
    })
    a.is_active = updated.is_active
  } catch {}
}

const remove = async (a: Automation) => {
  if (!await confirmDialog(`Remover automação "${a.name}"?`, { title: 'Remover automação' })) return
  try {
    await api(`/api/automations/${a.id}/`, { method: 'DELETE' })
    automations.value = automations.value.filter(x => x.id !== a.id)
  } catch {}
}

const create = async () => {
  try {
    const created = await api<Automation>('/api/automations/', {
      method: 'POST',
      body: {
        name: 'Nova automação',
        trigger_type: triggers.value[0]?.type ?? 'contact.created',
        trigger_filters: {},
        is_active: false,
        steps: [],
      },
    })
    await navigateTo(`/automations/${created.id}`)
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao criar'
  }
}

onMounted(fetchAll)
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 md:px-8 py-8">
    <div class="mb-8 flex items-end justify-between gap-4">
      <div>
        <p class="field-label mb-0.5">Organização</p>
        <h1 class="text-xl font-medium text-white tracking-tight">Automações</h1>
        <p class="text-xs font-mono text-neutral-600 mt-1">Fluxos automáticos disparados por eventos do sistema.</p>
      </div>
      <button @click="create" class="btn-primary !w-auto px-5 py-3">
        <div class="corner-tl"></div>
        <div class="corner-br"></div>
        <span class="text-white text-xs font-mono uppercase tracking-wider">+ Nova</span>
      </button>
    </div>

    <p v-if="error" class="text-xs font-mono text-red-400 mb-3">{{ error }}</p>

    <div v-if="loading" class="space-y-2">
      <div v-for="i in 4" :key="i" class="h-16 bg-white/5 animate-pulse"></div>
    </div>

    <div v-else-if="automations.length === 0" class="flex flex-col items-center justify-center py-16 border border-white/5 text-center">
      <Icon icon="solar:bolt-circle-bold-duotone" class="text-4xl text-white/10 mb-3" />
      <p class="text-xs font-mono text-neutral-700">Nenhuma automação criada ainda.</p>
    </div>

    <div v-else class="space-y-px">
      <div
        v-for="a in automations"
        :key="a.id"
        class="bg-surface border border-white/5 px-5 py-4 flex items-center gap-4"
      >
        <button
          @click="toggle(a)"
          class="w-10 h-5 rounded-full relative transition-colors shrink-0 p-0.5"
          :class="a.is_active ? 'bg-accent' : 'bg-white/10'"
          :title="a.is_active ? 'Desativar' : 'Ativar'"
        >
          <span
            class="block w-4 h-4 rounded-full bg-white transition-transform"
            :class="a.is_active ? 'translate-x-5' : 'translate-x-0'"
          ></span>
        </button>

        <NuxtLink :to="`/automations/${a.id}`" class="flex-1 min-w-0">
          <p class="text-sm text-white truncate">{{ a.name }}</p>
          <p class="text-[10px] font-mono text-neutral-600 uppercase tracking-wider mt-0.5">
            {{ triggerLabel(a.trigger_type) }} · {{ a.steps_count }} {{ a.steps_count === 1 ? 'passo' : 'passos' }}
          </p>
        </NuxtLink>

        <NuxtLink
          :to="`/automations/${a.id}/runs`"
          class="p-1.5 text-neutral-600 hover:text-neutral-300 transition-colors"
          title="Histórico"
        >
          <Icon icon="solar:history-bold-duotone" class="text-sm" />
        </NuxtLink>
        <NuxtLink
          :to="`/automations/${a.id}`"
          class="p-1.5 text-neutral-600 hover:text-neutral-300 transition-colors"
          title="Editar"
        >
          <Icon icon="solar:pen-bold-duotone" class="text-sm" />
        </NuxtLink>
        <button
          @click="remove(a)"
          class="p-1.5 text-neutral-600 hover:text-red-400 transition-colors"
          title="Remover"
        >
          <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-sm" />
        </button>
      </div>
    </div>
  </div>
</template>
