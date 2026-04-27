<script setup lang="ts">
import { Icon } from '@iconify/vue'

const api = useApi()
const router = useRouter()
const { confirm: confirmDialog } = useConfirm()

const campaigns = ref<any[]>([])
const loading = ref(true)
const modal = ref(false)

const fetchCampaigns = async () => {
  try {
    campaigns.value = await api<any[]>('/api/campaigns/')
  } catch {}
  finally { loading.value = false }
}

onMounted(fetchCampaigns)

const statusConfig: Record<string, { label: string; cls: string }> = {
  draft:     { label: 'Rascunho',  cls: 'text-neutral-400 border-white/10 bg-white/5' },
  running:   { label: 'Enviando',  cls: 'text-accent border-accent/30 bg-accent/5' },
  paused:    { label: 'Pausada',   cls: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/5' },
  finished:  { label: 'Concluída', cls: 'text-green-400 border-green-500/30 bg-green-500/5' },
  cancelled: { label: 'Cancelada', cls: 'text-red-400 border-red-500/30 bg-red-500/5' },
}

const formatDate = (d: string) =>
  new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })

const onCreated = (campaign: any) => {
  modal.value = false
  router.push(`/campaigns/${campaign.id}`)
}

const deleteCampaign = async (campaign: any, e: MouseEvent) => {
  e.stopPropagation()
  const ok = await confirmDialog(`Excluir "${campaign.name}"?`, { title: 'Excluir campanha' })
  if (!ok) return
  try {
    await api(`/api/campaigns/${campaign.id}/`, { method: 'DELETE' })
    campaigns.value = campaigns.value.filter(c => c.id !== campaign.id)
  } catch {}
}
</script>

<template>
  <div class="min-h-screen bg-canvas p-6">
    <div class="max-w-4xl mx-auto">

      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-sm font-mono uppercase tracking-widest text-white">Campanhas</h1>
          <p class="text-[11px] font-mono text-neutral-600 mt-0.5">Disparo em massa para múltiplos contatos</p>
        </div>
        <button
          @click="modal = true"
          class="flex items-center gap-2 px-3 py-2 bg-accent text-black text-xs font-mono uppercase tracking-wider hover:opacity-90 transition-opacity"
        >
          <Icon icon="solar:add-circle-bold-duotone" class="text-sm" />
          Nova Campanha
        </button>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-1.5">
        <div v-for="i in 4" :key="i" class="h-14 bg-white/5 animate-pulse" />
      </div>

      <!-- Empty -->
      <div v-else-if="!campaigns.length" class="flex flex-col items-center justify-center py-24 text-center">
        <Icon icon="solar:megaphone-bold-duotone" class="text-4xl text-white/10 mb-3" />
        <p class="text-xs font-mono text-neutral-700">Nenhuma campanha criada</p>
        <button @click="modal = true" class="mt-4 text-xs font-mono text-accent hover:underline">
          Criar primeira campanha
        </button>
      </div>

      <!-- List -->
      <div v-else class="space-y-1">
        <div
          v-for="c in campaigns"
          :key="c.id"
          @click="router.push(`/campaigns/${c.id}`)"
          class="flex items-center gap-4 px-4 py-3.5 border border-white/5 bg-surface hover:border-white/10 cursor-pointer transition-colors group"
        >
          <!-- Status -->
          <span
            class="px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest border shrink-0"
            :class="statusConfig[c.status]?.cls || statusConfig.draft.cls"
          >{{ statusConfig[c.status]?.label || c.status }}</span>

          <!-- Nome -->
          <p class="flex-1 text-xs text-white truncate min-w-0">{{ c.name }}</p>

          <!-- Progresso -->
          <div v-if="c.total_contacts > 0" class="hidden sm:flex items-center gap-2.5 shrink-0">
            <div class="w-24 h-1 bg-white/5">
              <div
                class="h-full transition-all"
                :class="c.status === 'finished' ? 'bg-green-500' : c.status === 'cancelled' ? 'bg-red-500/50' : 'bg-accent'"
                :style="`width: ${Math.round(((c.sent_count + c.failed_count) / c.total_contacts) * 100)}%`"
              />
            </div>
            <span class="text-[10px] font-mono text-neutral-500 w-16 text-right tabular-nums">
              {{ c.sent_count }}/{{ c.total_contacts }}
            </span>
          </div>
          <span v-else class="hidden sm:block text-[10px] font-mono text-neutral-700 shrink-0">0 contatos</span>

          <!-- Data -->
          <span class="hidden sm:block text-[10px] font-mono text-neutral-600 shrink-0">{{ formatDate(c.created_at) }}</span>

          <!-- Delete -->
          <button
            v-if="c.status === 'draft'"
            @click="deleteCampaign(c, $event)"
            class="opacity-0 group-hover:opacity-100 p-1 text-neutral-600 hover:text-red-400 transition-all shrink-0"
            title="Excluir"
          >
            <Icon icon="solar:trash-bin-minimalistic-bold-duotone" class="text-sm" />
          </button>
          <div v-else class="w-6 shrink-0" />
        </div>
      </div>

    </div>
  </div>

  <!-- Modal -->
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="modal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
        @click.self="modal = false"
      >
        <CampaignsCampaignForm @close="modal = false" @created="onCreated" />
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
