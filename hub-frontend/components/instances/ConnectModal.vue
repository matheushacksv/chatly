<script setup lang="ts">
import { Icon } from '@iconify/vue'

const props = defineProps<{
  open: boolean
  instance: any
}>()
const emit = defineEmits<{ close: []; connected: [] }>()

const api = useApi()
const activeTab = ref<'qr' | 'pair'>('qr')

// QR state
const qrCode = ref('')
const qrLoading = ref(false)
const qrError = ref('')
const isConnected = ref(false)
let consecutiveConnected = 0
let qrInterval: ReturnType<typeof setInterval> | null = null
let statusInterval: ReturnType<typeof setInterval> | null = null

// Pair state
const pairCode = ref('')
const pairPhone = ref('')
const pairLoading = ref(false)
const pairError = ref('')

const startQr = async () => {
  qrLoading.value = true
  qrError.value = ''
  qrCode.value = ''
  try {
    if (props.instance.status !== 'connecting') {
      await api(`/api/integrations/whatsapp/${props.instance.id}/connect`, {
        method: 'POST',
        body: {},
      })
    }
    const data = await api<{ qrcode: string; code: string }>(
      `/api/integrations/whatsapp/${props.instance.id}/qr`
    )
    qrCode.value = data.qrcode
  } catch (e: any) {
    if (e?.status === 400) {
      // EvoGO retornou 400 — instância pode já estar conectada
      await checkStatus()
    } else {
      qrError.value = e?.data?.detail || 'Erro ao gerar QR code'
    }
  } finally {
    qrLoading.value = false
  }

  isConnected.value = false
  consecutiveConnected = 0
  clearIntervals()
  qrInterval = setInterval(refreshQr, 25000)
  // Aguarda 20s antes de começar a verificar status
  setTimeout(() => {
    if (qrCode.value) {
      statusInterval = setInterval(checkStatus, 5000)
    }
  }, 20000)
}

const refreshQr = async () => {
  try {
    const data = await api<{ qrcode: string }>(
      `/api/integrations/whatsapp/${props.instance.id}/qr`
    )
    qrCode.value = data.qrcode
  } catch (e: any) {
    // 400 = EvoGO não tem QR para servir, provavelmente conectou
    if (e?.status === 400) {
      clearInterval(qrInterval!)
      qrInterval = null
      await checkStatus()
    }
  }
}

const checkStatus = async () => {
  try {
    const data = await api<any>(
      `/api/integrations/whatsapp/${props.instance.id}/status`
    )
    if (data.status === 'connected') {
      consecutiveConnected++
      // Só confirma conexão após 2 checks consecutivos como 'connected'
      if (consecutiveConnected >= 2) {
        clearIntervals()
        isConnected.value = true
      }
    } else {
      consecutiveConnected = 0
    }
  } catch {}
}

const getPairCode = async () => {
  if (!pairPhone.value.trim()) {
    pairError.value = 'Informe o número de telefone'
    return
  }
  pairLoading.value = true
  pairError.value = ''
  pairCode.value = ''
  try {
    // Sempre reconecta para garantir estado limpo no EvoGO
    await api(`/api/integrations/whatsapp/${props.instance.id}/connect`, {
      method: 'POST',
      body: {},
    })

    // Aguarda o EvoGO chegar no estado QR (instância pronta para autenticar)
    // Só quando o QR estiver disponível é que o pair code pode ser gerado
    let qrReady = false
    for (let i = 0; i < 10; i++) {
      await new Promise(resolve => setTimeout(resolve, 2000))
      try {
        const qrData = await api<{ qrcode: string }>(
          `/api/integrations/whatsapp/${props.instance.id}/qr`
        )
        if (qrData.qrcode) { qrReady = true; break }
      } catch {}
    }

    if (!qrReady) {
      pairError.value = 'Instância não ficou pronta a tempo. Tente novamente.'
      return
    }

    const data = await api<{ paircode: string }>(
      `/api/integrations/whatsapp/${props.instance.id}/pair`,
      { method: 'POST', body: { phone: pairPhone.value.trim() } }
    )

    if (!data.paircode) {
      pairError.value = 'Erro a retornar o código. Tente novamente.'
      return
    }
    pairCode.value = data.paircode

    // Reseta estado e inicia polling com delay, igual ao fluxo QR
    isConnected.value = false
    consecutiveConnected = 0
    clearIntervals()
    setTimeout(() => {
      if (pairCode.value) {
        statusInterval = setInterval(checkStatus, 5000)
      }
    }, 15000)
  } catch (e: any) {
    pairError.value = e?.data?.detail || 'Erro ao gerar código de par'
  } finally {
    pairLoading.value = false
  }
}

const clearIntervals = () => {
  if (qrInterval) { clearInterval(qrInterval); qrInterval = null }
  if (statusInterval) { clearInterval(statusInterval); statusInterval = null }
}

const handleClose = () => {
  clearIntervals()
  qrCode.value = ''
  pairCode.value = ''
  qrError.value = ''
  pairError.value = ''
  emit('close')
}

watch(() => props.open, (val) => {
  if (!val) handleClose()
})

onUnmounted(() => clearIntervals())
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="handleClose"></div>

        <div class="relative bg-surface border border-white/10 w-full max-w-md z-10">
          <!-- Corner accents -->
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <!-- Header -->
          <div class="px-8 pt-8 pb-4">
            <p class="field-label mb-1">{{ instance?.instance_name }}</p>
            <h2 class="text-xl font-medium text-white tracking-tight">Conectar instância</h2>
          </div>

          <!-- Tabs -->
          <div class="flex border-b border-white/5 px-8">
            <button
              @click="activeTab = 'qr'"
              class="pb-3 mr-6 text-xs font-mono uppercase tracking-widest transition-colors border-b-2 -mb-px"
              :class="activeTab === 'qr' ? 'text-accent border-accent' : 'text-neutral-500 border-transparent hover:text-white'"
            >
              QR Code
            </button>
            <button
              @click="activeTab = 'pair'"
              class="pb-3 text-xs font-mono uppercase tracking-widest transition-colors border-b-2 -mb-px"
              :class="activeTab === 'pair' ? 'text-accent border-accent' : 'text-neutral-500 border-transparent hover:text-white'"
            >
              Código de par
            </button>
          </div>

          <!-- QR Tab -->
          <div v-if="activeTab === 'qr'" class="p-8">
            <!-- Conexão confirmada -->
            <div v-if="isConnected" class="flex flex-col items-center py-6 text-center">
              <div class="w-12 h-12 bg-green-400/10 border border-green-400/20 flex items-center justify-center mb-4">
                <Icon icon="solar:check-circle-bold-duotone" class="text-2xl text-green-400" />
              </div>
              <p class="text-sm font-medium text-white mb-1">Conectado com sucesso!</p>
              <p class="text-xs font-mono text-neutral-500 mb-6">A instância está pronta para uso.</p>
              <button @click="() => { emit('connected'); handleClose() }" class="btn-primary !w-auto px-8 py-3">
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">Fechar</span>
              </button>
            </div>

            <template v-else>
              <p class="text-xs font-mono text-neutral-500 mb-6 leading-relaxed">
                Escaneie o QR code com o WhatsApp:<br />
                <span class="text-neutral-600">Configurações → Aparelhos conectados → Conectar</span>
              </p>

              <!-- QR image -->
              <div class="flex flex-col items-center mb-6">
                <div class="w-52 h-52 bg-canvas border border-white/10 flex items-center justify-center">
                  <div v-if="qrLoading" class="flex flex-col items-center gap-3">
                    <div class="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin"></div>
                    <p class="text-xs font-mono text-neutral-600">Gerando...</p>
                  </div>
                  <p v-else-if="qrError" class="text-xs font-mono text-red-400 text-center px-4">{{ qrError }}</p>
                  <img v-else-if="qrCode" :src="qrCode" alt="QR Code" class="w-full h-full object-contain p-2" />
                  <div v-else class="flex flex-col items-center gap-2">
                    <Icon icon="solar:qr-code-bold-duotone" class="text-5xl text-white/10" />
                    <p class="text-xs font-mono text-neutral-600">Clique em gerar</p>
                  </div>
              </div>

                <p v-if="qrCode" class="text-[11px] font-mono text-neutral-600 mt-3">
                  Aguardando scan... (expira em ~25s)
                </p>
              </div>

              <button
                @click="startQr"
                :disabled="qrLoading"
                class="btn-primary disabled:opacity-50"
              >
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">
                  {{ qrCode ? 'Atualizar QR' : 'Gerar QR Code' }}
                </span>
              </button>
            </template>
          </div>

          <!-- Pair Code Tab -->
          <div v-else class="p-8">
            <!-- Conexão confirmada -->
            <div v-if="isConnected" class="flex flex-col items-center py-6 text-center">
              <div class="w-12 h-12 bg-green-400/10 border border-green-400/20 flex items-center justify-center mb-4">
                <Icon icon="solar:check-circle-bold-duotone" class="text-2xl text-green-400" />
              </div>
              <p class="text-sm font-medium text-white mb-1">Conectado com sucesso!</p>
              <p class="text-xs font-mono text-neutral-500 mb-6">A instância está pronta para uso.</p>
              <button @click="() => { emit('connected'); handleClose() }" class="btn-primary !w-auto px-8 py-3">
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">Fechar</span>
              </button>
            </div>

            <template v-else>
              <p class="text-xs font-mono text-neutral-500 mb-6 leading-relaxed">
                Use o código de par para conectar sem escanear:<br />
                <span class="text-neutral-600">WhatsApp → Configurações → Aparelhos conectados → Vincular com número</span>
              </p>

              <!-- Phone input -->
              <div class="mb-5">
                <label class="field-label">Número de telefone</label>
                <div class="input-wrapper">
                  <input
                    v-model="pairPhone"
                    type="text"
                    placeholder="5511999999999"
                    class="input-field"
                  />
                </div>
                <p class="text-[11px] font-mono text-neutral-600 mt-1.5 pl-4">DDI + DDD + número, sem espaços</p>
              </div>

              <!-- Pair code display -->
              <div v-if="pairCode" class="bg-canvas border border-white/10 p-6 text-center mb-5">
                <p class="field-label mb-2">Código de pareamento</p>
                <p class="text-3xl font-mono text-accent tracking-widest font-medium">{{ pairCode }}</p>
                <p class="text-[11px] font-mono text-neutral-600 mt-3">Aguardando inserção no WhatsApp...</p>
              </div>

              <p v-if="pairError" class="text-xs font-mono text-red-400 mb-4">{{ pairError }}</p>

              <button
                @click="getPairCode"
                :disabled="pairLoading"
                class="btn-primary disabled:opacity-50"
              >
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">
                  {{ pairLoading ? 'Gerando...' : pairCode ? 'Gerar novo código' : 'Gerar código' }}
                </span>
              </button>
            </template>
          </div>

          <!-- Footer -->
          <div v-if="!isConnected" class="px-8 pb-6">
            <button
              @click="handleClose"
              class="w-full py-3 border border-white/5 text-neutral-500 text-xs font-mono uppercase tracking-wider hover:border-white/10 hover:text-neutral-300 transition-colors"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
