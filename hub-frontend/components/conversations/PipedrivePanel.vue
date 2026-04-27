<script setup lang="ts">
import { Icon } from '@iconify/vue'

const props = defineProps<{
  conversationId: number
  dealId: number
}>()

const emit = defineEmits<{ close: [] }>()

const api = useApi()

const data = ref<{ deal: any; stages: any[]; activities: any[] } | null>(null)
const loading = ref(true)
const saving = ref(false)
const selectedStage = ref<number | null>(null)

const statusLabel: Record<string, string> = {
  open: 'Aberto',
  won: 'Ganho',
  lost: 'Perdido',
  deleted: 'Excluído',
}

const statusClass: Record<string, string> = {
  open: 'text-green-400 border-green-500/30 bg-green-500/5',
  won: 'text-accent border-accent/30 bg-accent/5',
  lost: 'text-red-400 border-red-500/30 bg-red-500/5',
  deleted: 'text-neutral-500 border-white/10',
}

const activityIcon: Record<string, string> = {
  call: 'solar:phone-bold-duotone',
  meeting: 'solar:users-group-rounded-bold-duotone',
  task: 'solar:checklist-minimalistic-bold-duotone',
  deadline: 'solar:clock-circle-bold-duotone',
  email: 'solar:letter-bold-duotone',
  lunch: 'solar:cup-hot-bold-duotone',
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await api<{ deal: any; stages: any[]; activities: any[] }>(
      `/api/conversations/${props.conversationId}/pipedrive`
    )
    data.value = res
    selectedStage.value = res.deal?.stage_id ?? null
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

const moveStage = async () => {
  if (!selectedStage.value || saving.value || !data.value?.deal) return
  if (selectedStage.value === data.value.deal.stage_id) return
  saving.value = true
  try {
    await api(`/api/conversations/${props.conversationId}/pipedrive/stage`, {
      method: 'PATCH',
      body: { stage_id: selectedStage.value },
    })
    data.value.deal.stage_id = selectedStage.value
  } catch {
    selectedStage.value = data.value.deal.stage_id
  } finally {
    saving.value = false
  }
}

const completeActivity = async (activityId: number) => {
  if (saving.value) return
  saving.value = true
  try {
    await api(`/api/conversations/${props.conversationId}/pipedrive/activities/${activityId}/done`, {
      method: 'POST',
    })
    if (data.value) {
      data.value.activities = data.value.activities.filter(a => a.id !== activityId)
    }
  } catch {}
  finally { saving.value = false }
}

const formatDueDate = (date: string | null) => {
  if (!date) return null
  const d = new Date(date)
  const now = new Date()
  const diff = d.getTime() - now.getTime()
  const days = Math.ceil(diff / 86_400_000)
  if (days < 0) return { label: `${Math.abs(days)}d atraso`, overdue: true }
  if (days === 0) return { label: 'Hoje', overdue: false }
  if (days === 1) return { label: 'Amanhã', overdue: false }
  return { label: d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }), overdue: false }
}
</script>

<template>
  <div class="flex flex-col h-full bg-surface border-l border-white/10">

    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3.5 border-b border-white/5 shrink-0">
      <div class="flex items-center gap-2 min-w-0">
        <Icon icon="solar:case-round-bold-duotone" class="text-sm text-neutral-500 shrink-0" />
        <div class="min-w-0">
          <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500">Pipedrive</p>
          <p v-if="data?.deal" class="text-xs font-medium text-white truncate max-w-[160px]">{{ data.deal.title }}</p>
        </div>
      </div>
      <div class="flex items-center gap-1 shrink-0">
        <button
          @click="fetchData"
          :disabled="loading"
          class="p-1 text-neutral-500 hover:text-neutral-300 transition-colors disabled:opacity-40"
          title="Atualizar"
        >
          <Icon icon="solar:refresh-bold-duotone" class="text-base" :class="loading ? 'animate-spin' : ''" />
        </button>
        <button
          @click="emit('close')"
          class="p-1 text-neutral-500 hover:text-white transition-colors"
          title="Fechar"
        >
          <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
        </button>
      </div>
    </div>

    <!-- Corpo -->
    <div class="flex-1 overflow-y-auto">

      <!-- Skeleton -->
      <div v-if="loading" class="p-4 space-y-4">
        <div class="animate-pulse space-y-2">
          <div class="h-3 bg-white/5 rounded w-3/4"></div>
          <div class="h-3 bg-white/5 rounded w-1/2"></div>
        </div>
        <div class="animate-pulse space-y-2 mt-4">
          <div class="h-3 bg-white/5 rounded w-1/3"></div>
          <div class="h-8 bg-white/5 rounded w-full"></div>
        </div>
        <div class="animate-pulse space-y-2 mt-4">
          <div class="h-3 bg-white/5 rounded w-1/4"></div>
          <div v-for="i in 3" :key="i" class="h-10 bg-white/5 rounded w-full"></div>
        </div>
      </div>

      <!-- Sem deal -->
      <div v-else-if="!data?.deal" class="flex flex-col items-center justify-center h-48 text-center px-6">
        <Icon icon="solar:case-round-bold-duotone" class="text-4xl text-white/10 mb-3" />
        <p class="text-xs font-mono text-neutral-700">Deal não encontrado</p>
        <p class="text-[10px] font-mono text-neutral-700 mt-1">Integração pode estar inativa</p>
      </div>

      <template v-else>
        <div class="p-3 space-y-4">

          <!-- Status badge -->
          <div class="flex items-center gap-2">
            <span
              class="px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest border"
              :class="statusClass[data.deal.status] || statusClass.open"
            >
              {{ statusLabel[data.deal.status] || data.deal.status }}
            </span>
            <span v-if="data.deal.value" class="text-[10px] font-mono text-neutral-500">
              {{ data.deal.currency }} {{ Number(data.deal.value).toLocaleString('pt-BR') }}
            </span>
          </div>

          <!-- Etapa -->
          <div v-if="data.stages.length">
            <p class="field-label mb-1.5">Etapa</p>
            <div class="flex items-center gap-2">
              <select
                v-model="selectedStage"
                :disabled="saving"
                class="flex-1 bg-canvas border border-white/10 text-xs text-white font-mono px-2 py-1.5 outline-none focus:border-white/20 disabled:opacity-50 appearance-none"
                @change="moveStage"
              >
                <option
                  v-for="stage in data.stages"
                  :key="stage.id"
                  :value="stage.id"
                >{{ stage.name }}</option>
              </select>
              <div v-if="saving" class="w-3 h-3 border border-accent/30 border-t-accent rounded-full animate-spin shrink-0"></div>
            </div>
          </div>

          <!-- Atividades -->
          <div>
            <p class="field-label mb-1.5">Atividades pendentes</p>

            <div v-if="!data.activities.length" class="py-4 text-center">
              <p class="text-[10px] font-mono text-neutral-700">Nenhuma atividade pendente</p>
            </div>

            <div v-else class="space-y-1.5">
              <div
                v-for="activity in data.activities"
                :key="activity.id"
                class="flex items-start gap-2.5 px-3 py-2.5 border border-white/5 bg-canvas group"
              >
                <!-- Checkbox -->
                <button
                  @click="completeActivity(activity.id)"
                  :disabled="saving"
                  class="mt-0.5 w-3.5 h-3.5 shrink-0 border border-white/20 hover:border-accent/50 hover:bg-accent/10 transition-colors disabled:opacity-40 flex items-center justify-center"
                  title="Marcar como concluída"
                >
                  <Icon icon="solar:check-read-bold-duotone" class="text-[8px] text-transparent group-hover:text-accent/50 transition-colors" />
                </button>

                <!-- Conteúdo -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-1.5 mb-0.5">
                    <Icon
                      :icon="activityIcon[activity.type] || 'solar:calendar-mark-bold-duotone'"
                      class="text-xs text-neutral-500 shrink-0"
                    />
                    <p class="text-xs text-white truncate">{{ activity.subject }}</p>
                  </div>
                  <p v-if="activity.note" class="text-[10px] font-mono text-neutral-500 mt-0.5 line-clamp-2 whitespace-pre-wrap">{{ activity.note }}</p>
                  <div v-if="activity.due_date" class="flex items-center gap-1 mt-0.5">
                    <span
                      class="text-[10px] font-mono"
                      :class="formatDueDate(activity.due_date)?.overdue ? 'text-red-400' : 'text-neutral-600'"
                    >
                      {{ formatDueDate(activity.due_date)?.label }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </template>
    </div>

    <!-- Footer -->
    <div class="border-t border-white/5 shrink-0 px-4 py-3">
      <a
        :href="`https://app.pipedrive.com/deal/${dealId}`"
        target="_blank"
        rel="noopener noreferrer"
        class="w-full flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-neutral-500 hover:text-accent transition-colors"
      >
        <Icon icon="solar:arrow-right-up-bold-duotone" class="text-sm" />
        Abrir no Pipedrive
      </a>
    </div>

  </div>
</template>
