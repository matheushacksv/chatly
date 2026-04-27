<script setup lang="ts">
import { Icon } from '@iconify/vue'

const emit = defineEmits<{ close: []; created: [campaign: any] }>()

const api = useApi()

const instances = ref<any[]>([])
const agents = ref<any[]>([])
const loading = ref(true)
const submitting = ref(false)
const error = ref('')

const form = reactive({
  name: '',
  instance_id: null as number | null,
  agent_id: null as number | null,
  ai_active: false,
  interval_min: 5,
  interval_max: 15,
  messages: [{ content: '' }] as { content: string }[],
})

onMounted(async () => {
  try {
    ;[instances.value, agents.value] = await Promise.all([
      api<any[]>('/api/integrations/whatsapp/'),
      api<any[]>('/api/agents/'),
    ])
    if (instances.value.length) form.instance_id = instances.value[0].id
  } catch {}
  finally { loading.value = false }
})

watch(() => form.agent_id, (val) => { if (!val) form.ai_active = false })

const addMessage = () => form.messages.push({ content: '' })
const removeMessage = (i: number) => { if (form.messages.length > 1) form.messages.splice(i, 1) }

const submit = async () => {
  error.value = ''
  if (!form.name.trim()) { error.value = 'Informe o nome da campanha'; return }
  if (!form.instance_id) { error.value = 'Selecione uma instância'; return }
  if (form.messages.some(m => !m.content.trim())) { error.value = 'Preencha todas as variantes de mensagem'; return }
  if (form.interval_min > form.interval_max) { error.value = 'Intervalo mínimo não pode ser maior que o máximo'; return }

  submitting.value = true
  try {
    const campaign = await api<any>('/api/campaigns/', {
      method: 'POST',
      body: {
        name: form.name.trim(),
        instance_id: form.instance_id,
        agent_id: form.agent_id || null,
        ai_active: form.ai_active,
        interval_min: form.interval_min,
        interval_max: form.interval_max,
        messages: form.messages.map(m => ({ content: m.content.trim() })),
      },
    })
    emit('created', campaign)
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao criar campanha'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="bg-surface border border-white/10 w-full max-w-lg max-h-[90vh] flex flex-col">

    <!-- Header -->
    <div class="flex items-center justify-between px-5 py-4 border-b border-white/5 shrink-0">
      <p class="text-xs font-mono uppercase tracking-widest text-white">Nova Campanha</p>
      <button @click="emit('close')" class="text-neutral-500 hover:text-white transition-colors">
        <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center py-12">
      <div class="w-4 h-4 border border-accent/30 border-t-accent rounded-full animate-spin" />
    </div>

    <!-- Form -->
    <div v-else class="flex-1 overflow-y-auto p-5 space-y-4">

      <!-- Nome -->
      <div>
        <p class="field-label mb-1.5">Nome</p>
        <input
          v-model="form.name"
          type="text"
          placeholder="Ex: Promoção de Natal"
          class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20 placeholder:text-neutral-600"
          @keydown.enter="submit"
        />
      </div>

      <!-- Instância -->
      <div>
        <p class="field-label mb-1.5">Instância WhatsApp</p>
        <select
          v-model="form.instance_id"
          class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20 appearance-none"
        >
          <option v-for="inst in instances" :key="inst.id" :value="inst.id">
            {{ inst.instance_name }}{{ inst.phone_number ? ` (${inst.phone_number})` : '' }}
          </option>
        </select>
        <p v-if="!instances.length" class="text-[10px] font-mono text-red-400 mt-1">Nenhuma instância encontrada</p>
      </div>

      <!-- Agente -->
      <div>
        <p class="field-label mb-1.5">Agente de IA <span class="text-neutral-600">(opcional)</span></p>
        <select
          v-model="form.agent_id"
          class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20 appearance-none"
        >
          <option :value="null">Nenhum</option>
          <option v-for="a in agents" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>

        <label
          v-if="form.agent_id"
          class="flex items-center gap-2.5 mt-2.5 cursor-pointer"
          @click="form.ai_active = !form.ai_active"
        >
          <div
            class="w-7 h-4 rounded-full relative transition-colors shrink-0"
            :class="form.ai_active ? 'bg-accent' : 'bg-white/10'"
          >
            <div
              class="absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all"
              :class="form.ai_active ? 'left-3.5' : 'left-0.5'"
            />
          </div>
          <span class="text-xs font-mono text-neutral-400">IA responde automaticamente às respostas</span>
        </label>
      </div>

      <!-- Intervalo -->
      <div>
        <p class="field-label mb-1.5">Intervalo entre disparos <span class="text-neutral-600">(segundos)</span></p>
        <div class="flex items-center gap-3">
          <div class="flex-1">
            <p class="text-[10px] font-mono text-neutral-600 mb-1">Mínimo</p>
            <input
              v-model.number="form.interval_min"
              type="number" min="1" max="3600"
              class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20"
            />
          </div>
          <span class="text-neutral-600 mt-4 shrink-0">—</span>
          <div class="flex-1">
            <p class="text-[10px] font-mono text-neutral-600 mb-1">Máximo</p>
            <input
              v-model.number="form.interval_max"
              type="number" min="1" max="3600"
              class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20"
            />
          </div>
        </div>
      </div>

      <!-- Mensagens variantes -->
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <p class="field-label">Variantes de mensagem</p>
          <button
            @click="addMessage"
            class="text-[10px] font-mono text-accent hover:underline flex items-center gap-1"
          >
            <Icon icon="solar:add-circle-bold-duotone" class="text-xs" />
            Adicionar
          </button>
        </div>
        <p class="text-[10px] font-mono text-neutral-600 mb-2.5">
          Uma variante é sorteada por contato. Use
          <code class="text-accent/80">{nome}</code> e
          <code class="text-accent/80">{telefone}</code> como variáveis.
        </p>

        <div class="space-y-2">
          <div v-for="(msg, i) in form.messages" :key="i" class="flex gap-2 items-start">
            <div class="flex-1">
              <p v-if="form.messages.length > 1" class="text-[10px] font-mono text-neutral-600 mb-1">Variante {{ i + 1 }}</p>
              <textarea
                v-model="msg.content"
                rows="3"
                :placeholder="`Olá {nome}, temos uma oferta especial para você!`"
                class="w-full bg-canvas border border-white/10 text-xs text-white font-mono px-3 py-2 outline-none focus:border-white/20 resize-none placeholder:text-neutral-600"
              />
            </div>
            <button
              v-if="form.messages.length > 1"
              @click="removeMessage(i)"
              class="mt-5 text-neutral-600 hover:text-red-400 transition-colors shrink-0"
            >
              <Icon icon="solar:trash-bin-minimalistic-bold-duotone" class="text-sm" />
            </button>
          </div>
        </div>
      </div>

      <p v-if="error" class="text-[10px] font-mono text-red-400">{{ error }}</p>
    </div>

    <!-- Footer -->
    <div class="px-5 py-4 border-t border-white/5 shrink-0 flex justify-end gap-2">
      <button
        @click="emit('close')"
        class="px-3 py-2 text-xs font-mono text-neutral-400 hover:text-white border border-white/10 hover:border-white/20 transition-colors"
      >
        Cancelar
      </button>
      <button
        @click="submit"
        :disabled="submitting || loading"
        class="px-4 py-2 text-xs font-mono bg-accent text-black uppercase tracking-wider disabled:opacity-50 hover:opacity-90 transition-opacity flex items-center gap-2"
      >
        <div v-if="submitting" class="w-3 h-3 border border-black/30 border-t-black rounded-full animate-spin" />
        Criar Campanha
      </button>
    </div>

  </div>
</template>
