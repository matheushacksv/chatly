<script setup lang="ts">
import { Icon } from '@iconify/vue'

const props = defineProps<{ instance: any }>()
const emit = defineEmits(['close'])

const api = useApi()

const loading = ref(true)
const saving = ref(false)
const deleting = ref(false)
const error = ref('')

const isActive = ref(true)
const members = ref<{ user_id: number; user_name: string; percentage: number; assignment_count: number }[]>([])
const orgMembers = ref<any[]>([])
const addUserId = ref<number | null>(null)

const totalPercentage = computed(() => members.value.reduce((sum, m) => sum + (m.percentage || 0), 0))
const isValid = computed(() => members.value.length > 0 && totalPercentage.value === 100)

const availableToAdd = computed(() =>
  orgMembers.value.filter(m => !members.value.some(qm => qm.user_id === m.id))
)

const fetchData = async () => {
  loading.value = true
  error.value = ''
  try {
    const [membersRes, queueRes] = await Promise.allSettled([
      api<any[]>('/api/org/members'),
      api<any>(`/api/integrations/whatsapp/${props.instance.id}/queue`),
    ])
    if (membersRes.status === 'fulfilled') orgMembers.value = membersRes.value
    if (queueRes.status === 'fulfilled') {
      isActive.value = queueRes.value.is_active
      members.value = queueRes.value.members
    }
  } catch {}
  finally { loading.value = false }
}

onMounted(fetchData)

const addMember = () => {
  if (!addUserId.value) return
  const user = orgMembers.value.find(m => m.id === addUserId.value)
  if (!user) return
  members.value.push({ user_id: user.id, user_name: user.name || user.email, percentage: 0, assignment_count: 0 })
  addUserId.value = null
}

const removeMember = (idx: number) => {
  members.value.splice(idx, 1)
}

const save = async () => {
  if (!isValid.value) return
  saving.value = true
  error.value = ''
  try {
    await api(`/api/integrations/whatsapp/${props.instance.id}/queue`, {
      method: 'PUT',
      body: {
        is_active: isActive.value,
        members: members.value.map(m => ({ user_id: m.user_id, percentage: m.percentage })),
      },
    })
    emit('close')
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao salvar fila'
  } finally {
    saving.value = false
  }
}

const deleteQueue = async () => {
  deleting.value = true
  error.value = ''
  try {
    await api(`/api/integrations/whatsapp/${props.instance.id}/queue`, { method: 'DELETE' })
    emit('close')
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao remover fila'
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div class="bg-surface border border-white/10 w-full max-w-lg shadow-2xl flex flex-col max-h-[90vh]">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <div>
            <p class="field-label mb-0.5">Fila de Atendimento</p>
            <p class="text-white text-sm font-mono">{{ instance.instance_name }}</p>
          </div>
          <button @click="emit('close')" class="text-neutral-500 hover:text-white transition-colors">
            <Icon icon="solar:close-circle-bold-duotone" class="text-xl" />
          </button>
        </div>

        <!-- Body -->
        <div v-if="loading" class="flex-1 flex items-center justify-center py-12">
          <span class="text-neutral-600 text-xs font-mono">Carregando...</span>
        </div>

        <div v-else class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          <!-- Toggle ativo -->
          <label class="flex items-center gap-3 cursor-pointer">
            <div
              @click="isActive = !isActive"
              class="w-9 h-5 rounded-full transition-colors relative cursor-pointer"
              :class="isActive ? 'bg-accent' : 'bg-neutral-700'"
            >
              <div
                class="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                :class="isActive ? 'translate-x-4' : 'translate-x-0.5'"
              />
            </div>
            <span class="text-sm text-neutral-300 font-mono">Fila ativa</span>
          </label>

          <!-- Lista de membros -->
          <div v-if="members.length > 0" class="space-y-2">
            <p class="field-label">Membros</p>
            <div
              v-for="(member, idx) in members"
              :key="member.user_id"
              class="flex items-center gap-3 bg-canvas border border-white/5 px-4 py-3"
            >
              <div class="flex-1 min-w-0">
                <p class="text-sm text-white truncate">{{ member.user_name }}</p>
                <p class="text-[10px] font-mono text-neutral-600">{{ member.assignment_count }} atribuições</p>
              </div>
              <div class="flex items-center gap-1.5 shrink-0">
                <input
                  v-model.number="member.percentage"
                  type="number"
                  min="1"
                  max="100"
                  class="w-14 bg-surface border border-white/10 text-sm text-white font-mono px-2 py-1 text-center outline-none focus:border-white/30"
                />
                <span class="text-xs font-mono text-neutral-600">%</span>
              </div>
              <button @click="removeMember(idx)" class="text-neutral-600 hover:text-red-500 transition-colors shrink-0">
                <Icon icon="solar:close-circle-bold-duotone" class="text-base" />
              </button>
            </div>

            <!-- Total -->
            <div class="flex justify-end pt-1">
              <span
                class="text-xs font-mono"
                :class="totalPercentage === 100 ? 'text-green-400' : 'text-red-500'"
              >
                Total: {{ totalPercentage }}%{{ totalPercentage === 100 ? ' ✓' : ' (deve ser 100%)' }}
              </span>
            </div>
          </div>

          <div v-else class="text-center py-6">
            <p class="text-xs font-mono text-neutral-600">Nenhum membro na fila</p>
          </div>

          <!-- Adicionar membro -->
          <div v-if="availableToAdd.length > 0" class="flex items-center gap-2">
            <select
              v-model="addUserId"
              class="flex-1 bg-canvas border border-white/10 text-sm text-neutral-300 font-mono px-3 py-2 outline-none focus:border-white/20"
            >
              <option :value="null" disabled>Selecionar membro...</option>
              <option v-for="m in availableToAdd" :key="m.id" :value="m.id">
                {{ m.name || m.email }}
              </option>
            </select>
            <button
              @click="addMember"
              :disabled="!addUserId"
              class="px-4 py-2 text-[10px] font-mono uppercase tracking-widest border border-white/10 text-neutral-400 hover:border-accent hover:text-accent transition-colors disabled:opacity-30"
            >
              Adicionar
            </button>
          </div>

          <!-- Erro -->
          <p v-if="error" class="text-xs font-mono text-red-500">{{ error }}</p>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between px-6 py-4 border-t border-white/5 gap-3">
          <button
            v-if="members.length > 0 || !loading"
            @click="deleteQueue"
            :disabled="deleting"
            class="text-[10px] font-mono uppercase tracking-widest text-neutral-600 hover:text-red-500 transition-colors disabled:opacity-50"
          >
            {{ deleting ? 'Removendo...' : 'Remover fila' }}
          </button>
          <div class="flex items-center gap-2 ml-auto">
            <button
              @click="emit('close')"
              class="px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-neutral-500 hover:text-white transition-colors"
            >
              Cancelar
            </button>
            <button
              @click="save"
              :disabled="saving || !isValid || loading"
              class="px-5 py-2 text-[10px] font-mono uppercase tracking-widest border border-accent/30 text-accent hover:bg-accent/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {{ saving ? 'Salvando...' : 'Salvar fila' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
