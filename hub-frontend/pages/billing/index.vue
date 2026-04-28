<script setup lang="ts">
import { Icon } from '@iconify/vue'

useHead({ title: 'Faturamento' })

const api = useApi()
const config = useRuntimeConfig()

const subscription = ref<any>(null)
const plans = ref<any[]>([])
const loading = ref(true)
const checkoutLoading = ref<string | null>(null)
const portalLoading = ref(false)
const extraLoading = ref(false)
const extraQty = ref(1)
const error = ref('')

const baseUrl = computed(() => process.client ? window.location.origin : '')

const fetchData = async () => {
  loading.value = true
  try {
    ;[subscription.value, plans.value] = await Promise.all([
      api<any>('/api/billing/'),
      api<any[]>('/api/billing/plans'),
    ])
  } catch {}
  finally { loading.value = false }
}

onMounted(async () => {
  const portalReturn = route.query.portal_return === '1'
  if (portalReturn) {
    // aguarda webhook processar antes de buscar dados atualizados
    await new Promise(r => setTimeout(r, 2500))
  }
  await fetchData()
})

const currentPlan = computed(() => subscription.value?.plan)

const usagePct = (used: number, max: number | null) => {
  if (max === null) return 0
  return Math.min(Math.round((used / max) * 100), 100)
}

const formatLimit = (val: number | null) => val === null ? '∞' : val.toLocaleString('pt-BR')

const checkout = async (planSlug: string) => {
  checkoutLoading.value = planSlug
  error.value = ''
  try {
    const { url } = await api<{ url: string }>('/api/billing/checkout', {
      method: 'POST',
      body: {
        plan_slug: planSlug,
        success_url: `${baseUrl.value}/billing?success=1`,
        cancel_url: `${baseUrl.value}/billing`,
      },
    })
    window.location.href = url
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao iniciar checkout'
  } finally {
    checkoutLoading.value = null
  }
}

const openPortal = async () => {
  portalLoading.value = true
  error.value = ''
  try {
    const { url } = await api<{ url: string }>('/api/billing/portal', {
      method: 'POST',
      body: { return_url: `${baseUrl.value}/billing?portal_return=1` },
    })
    window.location.href = url
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao abrir portal'
  } finally {
    portalLoading.value = false
  }
}

const addExtra = async () => {
  if (extraQty.value < 1) return
  extraLoading.value = true
  error.value = ''
  try {
    subscription.value = await api<any>('/api/billing/extra-instances', {
      method: 'POST',
      body: { quantity: extraQty.value },
    })
    extraQty.value = 1
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao adicionar instâncias'
  } finally {
    extraLoading.value = false
  }
}

const route = useRoute()
const successMsg = computed(() => route.query.success === '1')
</script>

<template>
  <div class="p-4 md:p-8 max-w-3xl">
    <!-- Header -->
    <div class="mb-10">
      <p class="field-label mb-1">Conta</p>
      <h1 class="text-2xl font-medium text-white tracking-tight">Plano</h1>
    </div>

    <!-- Success banner -->
    <div v-if="successMsg" class="mb-6 bg-green-500/10 border border-green-500/30 px-4 py-3 text-xs font-mono text-green-400">
      Plano atualizado com sucesso!
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="bg-surface border border-white/5 p-6 animate-pulse h-20" />
    </div>

    <template v-else-if="subscription">
      <!-- Plano atual -->
      <div class="bg-surface border border-white/5 p-6 mb-4">
        <div class="flex items-start justify-between gap-4 mb-6">
          <div>
            <p class="field-label mb-1">Plano atual</p>
            <div class="flex items-center gap-3">
              <span class="text-white text-xl font-medium">{{ currentPlan?.name }}</span>
              <span
                class="text-[9px] font-mono uppercase tracking-widest px-2 py-0.5 border"
                :class="{
                  'border-green-500/40 text-green-400': subscription.status === 'active',
                  'border-yellow-500/40 text-yellow-400': subscription.status === 'past_due',
                  'border-neutral-700 text-neutral-500': ['free', 'canceled'].includes(subscription.status),
                  'border-accent/40 text-accent': subscription.status === 'trialing',
                }"
              >{{ subscription.status }}</span>
            </div>
            <p v-if="subscription.current_period_end" class="text-[10px] font-mono text-neutral-600 mt-1">
              Renova em {{ new Date(subscription.current_period_end).toLocaleDateString('pt-BR') }}
            </p>
          </div>
          <button
            v-if="subscription.stripe_customer_id || subscription.status !== 'free'"
            @click="openPortal"
            :disabled="portalLoading"
            class="shrink-0 px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-white/10 text-neutral-400 hover:border-white/30 hover:text-white transition-colors disabled:opacity-40"
          >
            {{ portalLoading ? 'Abrindo...' : 'Gerenciar cobrança' }}
          </button>
        </div>

        <!-- Uso -->
        <div class="space-y-4">
          <!-- Instâncias -->
          <div>
            <div class="flex justify-between mb-1.5">
              <span class="text-[10px] font-mono text-neutral-500 uppercase tracking-widest">Instâncias</span>
              <span class="text-[10px] font-mono" :class="subscription.usage.instances_used >= (subscription.max_instances_total ?? Infinity) ? 'text-red-500' : 'text-neutral-400'">
                {{ subscription.usage.instances_used }} / {{ formatLimit(subscription.max_instances_total) }}
              </span>
            </div>
            <div class="h-1 bg-neutral-900 w-full">
              <div
                class="h-1 transition-all"
                :class="subscription.max_instances_total && subscription.usage.instances_used >= subscription.max_instances_total ? 'bg-red-500' : 'bg-accent'"
                :style="{ width: currentPlan?.is_unlimited ? '0%' : `${usagePct(subscription.usage.instances_used, subscription.max_instances_total)}%` }"
              />
            </div>
          </div>

          <!-- Membros -->
          <div>
            <div class="flex justify-between mb-1.5">
              <span class="text-[10px] font-mono text-neutral-500 uppercase tracking-widest">Membros</span>
              <span class="text-[10px] font-mono" :class="subscription.usage.members_used >= (currentPlan?.max_members ?? Infinity) ? 'text-red-500' : 'text-neutral-400'">
                {{ subscription.usage.members_used }} / {{ formatLimit(currentPlan?.max_members) }}
              </span>
            </div>
            <div class="h-1 bg-neutral-900 w-full">
              <div
                class="h-1 transition-all"
                :class="currentPlan?.max_members && subscription.usage.members_used >= currentPlan?.max_members ? 'bg-red-500' : 'bg-accent'"
                :style="{ width: currentPlan?.is_unlimited ? '0%' : `${usagePct(subscription.usage.members_used, currentPlan?.max_members)}%` }"
              />
            </div>
          </div>

          <!-- Contatos -->
          <div>
            <div class="flex justify-between mb-1.5">
              <span class="text-[10px] font-mono text-neutral-500 uppercase tracking-widest">Contatos</span>
              <span class="text-[10px] font-mono" :class="subscription.usage.contacts_used >= (currentPlan?.max_contacts ?? Infinity) ? 'text-red-500' : 'text-neutral-400'">
                {{ subscription.usage.contacts_used.toLocaleString('pt-BR') }} / {{ formatLimit(currentPlan?.max_contacts) }}
              </span>
            </div>
            <div class="h-1 bg-neutral-900 w-full">
              <div
                class="h-1 transition-all"
                :class="currentPlan?.max_contacts && subscription.usage.contacts_used >= currentPlan?.max_contacts ? 'bg-red-500' : 'bg-accent'"
                :style="{ width: currentPlan?.is_unlimited ? '0%' : `${usagePct(subscription.usage.contacts_used, currentPlan?.max_contacts)}%` }"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Instâncias extras (só se tiver subscription ativa com preço configurado) -->
      <div v-if="subscription.status === 'active' && !currentPlan?.is_unlimited" class="bg-surface border border-white/5 px-6 py-5 mb-4">
        <p class="field-label mb-3">Instâncias extras</p>
        <div class="flex items-center gap-3">
          <input
            v-model.number="extraQty"
            type="number"
            min="1"
            max="20"
            class="w-16 bg-canvas border border-white/10 text-sm text-white font-mono px-3 py-2 text-center outline-none focus:border-white/30"
          />
          <span class="text-xs font-mono text-neutral-600">instância(s)</span>
          <button
            @click="addExtra"
            :disabled="extraLoading || extraQty < 1"
            class="px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-accent/30 text-accent hover:bg-accent/5 transition-colors disabled:opacity-40"
          >
            {{ extraLoading ? 'Adicionando...' : 'Adicionar' }}
          </button>
        </div>
        <p v-if="subscription.extra_instances > 0" class="text-[10px] font-mono text-neutral-600 mt-2">
          {{ subscription.extra_instances }} instância(s) extra(s) ativas no plano
        </p>
      </div>

      <!-- Planos disponíveis para upgrade -->
      <div v-if="plans.length > 0 && !currentPlan?.is_unlimited">
        <p class="field-label mb-3">Planos disponíveis</p>
        <div class="space-y-2">
          <div
            v-for="plan in plans"
            :key="plan.id"
            class="bg-surface border transition-colors flex items-center justify-between px-5 py-4 gap-4"
            :class="plan.slug === currentPlan?.slug ? 'border-accent/40' : 'border-white/5'"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-sm text-white font-medium">{{ plan.name }}</span>
                <span v-if="plan.slug === currentPlan?.slug" class="text-[9px] font-mono uppercase tracking-widest text-accent border border-accent/30 px-1.5 py-0.5">atual</span>
              </div>
              <div class="flex flex-wrap gap-x-4 gap-y-0.5">
                <span class="text-[10px] font-mono text-neutral-600">{{ plan.max_instances }} instância{{ plan.max_instances !== 1 ? 's' : '' }}</span>
                <span class="text-[10px] font-mono text-neutral-600">{{ plan.max_members }} membros</span>
                <span class="text-[10px] font-mono text-neutral-600">{{ (plan.max_contacts || 0).toLocaleString('pt-BR') }} contatos</span>
              </div>
            </div>
            <div class="shrink-0 text-right">
              <p v-if="plan.base_price > 0" class="text-sm text-white font-mono mb-1">
                R$ {{ Number(plan.base_price).toLocaleString('pt-BR', { minimumFractionDigits: 2 }) }}<span class="text-neutral-600 text-[10px]">/mês</span>
              </p>
              <button
                v-if="plan.slug !== currentPlan?.slug && plan.stripe_price_id"
                @click="checkout(plan.slug)"
                :disabled="!!checkoutLoading"
                class="px-4 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-accent/30 text-accent hover:bg-accent/5 transition-colors disabled:opacity-40"
              >
                {{ checkoutLoading === plan.slug ? 'Aguarde...' : 'Assinar' }}
              </button>
              <span v-else-if="plan.slug !== currentPlan?.slug && !plan.stripe_price_id" class="text-[10px] font-mono text-neutral-700">Em breve</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Erro -->
      <p v-if="error" class="mt-4 text-xs font-mono text-red-500">{{ error }}</p>
    </template>
  </div>
</template>
