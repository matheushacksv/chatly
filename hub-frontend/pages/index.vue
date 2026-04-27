<script setup lang="ts">
import { Icon } from '@iconify/vue'

const api = useApi()
const authStore = useAuthStore()

const loading = ref(true)
const instances = ref<any[]>([])
const metrics = ref({
  openConversations: 0,
  closedConversations: 0,
  connectedInstances: 0,
  totalAgents: 0,
})

onMounted(async () => {
  if (!authStore.user && authStore.accessToken) {
    await authStore.fetchMe()
  }

  try {
    const [instancesData, openConvs, closedConvs, agentsData] = await Promise.all([
      api<any[]>('/api/integrations/whatsapp/'),
      api<any[]>('/api/conversations/?status=open'),
      api<any[]>('/api/conversations/?status=closed'),
      api<any[]>('/api/agents/'),
    ])

    instances.value = instancesData
    metrics.value = {
      openConversations: openConvs.length,
      closedConversations: closedConvs.length,
      connectedInstances: instancesData.filter((i) => i.status === 'connected').length,
      totalAgents: agentsData.length,
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

const statusColor = (status: string) => ({
  'bg-green-400': status === 'connected',
  'bg-yellow-400': status === 'connecting',
  'bg-red-500': status === 'disconnected',
})

const statusTextColor = (status: string) => ({
  'text-green-400': status === 'connected',
  'text-yellow-400': status === 'connecting',
  'text-red-500': status === 'disconnected',
})
</script>

<template>
  <div class="p-4 md:p-8 max-w-5xl">
    <!-- Header -->
    <div class="mb-10">
      <p class="field-label mb-1">Dashboard</p>
      <h1 class="text-2xl font-medium text-white tracking-tight">{{ authStore.user?.org_name }}</h1>
    </div>

    <!-- Skeleton -->
    <div v-if="loading" class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
      <div v-for="i in 4" :key="i" class="bg-surface border border-white/5 p-6 animate-pulse">
        <div class="h-2.5 bg-white/5 rounded mb-4 w-2/3"></div>
        <div class="h-8 bg-white/5 rounded w-1/3"></div>
      </div>
    </div>

    <!-- Metrics -->
    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
      <div class="bg-surface border border-white/5 p-6 relative overflow-hidden hover:border-white/10 transition-colors">
        <div class="beam-border-h"></div>
        <p class="field-label mb-3">Conversas abertas</p>
        <p class="text-3xl font-medium text-white">{{ metrics.openConversations }}</p>
        <Icon icon="solar:chat-round-dots-bold-duotone" class="absolute bottom-4 right-4 text-4xl text-white/5" />
      </div>

      <div class="bg-surface border border-white/5 p-6 relative overflow-hidden hover:border-white/10 transition-colors">
        <p class="field-label mb-3">Conversas fechadas</p>
        <p class="text-3xl font-medium text-white">{{ metrics.closedConversations }}</p>
        <Icon icon="solar:check-circle-bold-duotone" class="absolute bottom-4 right-4 text-4xl text-white/5" />
      </div>

      <div class="bg-surface border border-white/5 p-6 relative overflow-hidden hover:border-white/10 transition-colors">
        <p class="field-label mb-3">Instâncias ativas</p>
        <p class="text-3xl font-medium text-white">{{ metrics.connectedInstances }}</p>
        <Icon icon="solar:smartphone-2-bold-duotone" class="absolute bottom-4 right-4 text-4xl text-white/5" />
      </div>

      <div class="bg-surface border border-white/5 p-6 relative overflow-hidden hover:border-white/10 transition-colors">
        <p class="field-label mb-3">Agentes de IA</p>
        <p class="text-3xl font-medium text-white">{{ metrics.totalAgents }}</p>
        <Icon icon="solar:cpu-bolt-bold-duotone" class="absolute bottom-4 right-4 text-4xl text-white/5" />
      </div>
    </div>

    <!-- Instances status -->
    <div v-if="!loading">
      <div class="flex items-center justify-between mb-4">
        <p class="field-label">Status das instâncias</p>
        <NuxtLink to="/instances" class="text-xs font-mono text-neutral-400 hover:text-accent transition-colors uppercase tracking-widest">
          Gerenciar →
        </NuxtLink>
      </div>

      <div v-if="instances.length === 0" class="bg-surface border border-white/5 p-6 text-center">
        <p class="text-xs font-mono text-neutral-600">Nenhuma instância configurada.</p>
        <NuxtLink to="/instances" class="text-xs font-mono text-accent mt-2 inline-block hover:underline">
          Criar instância →
        </NuxtLink>
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="instance in instances"
          :key="instance.id"
          class="bg-surface border border-white/5 px-5 py-4 flex items-center justify-between hover:border-white/10 transition-colors"
        >
          <div class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full shrink-0" :class="statusColor(instance.status)"></div>
            <div>
              <p class="text-sm text-white">{{ instance.instance_name }}</p>
              <p v-if="instance.phone_number" class="text-xs font-mono text-neutral-500 mt-0.5">{{ instance.phone_number }}</p>
            </div>
          </div>
          <span class="text-xs font-mono uppercase tracking-widest" :class="statusTextColor(instance.status)">
            {{ instance.status }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
