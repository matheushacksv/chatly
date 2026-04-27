<script setup lang="ts">
import { Icon } from '@iconify/vue'

const emit = defineEmits<{ close: []; imported: [] }>()

const api = useApi()

type Step = 'idle' | 'loading' | 'result'
const step = ref<Step>('idle')
const dragOver = ref(false)
const error = ref('')

interface ImportResult {
  created: number
  skipped: number
  errors: { row: number; reason: string }[]
}
const result = ref<ImportResult | null>(null)

const reset = () => {
  step.value = 'idle'
  error.value = ''
  result.value = null
}

const close = () => {
  reset()
  emit('close')
}

const downloadTemplate = () => {
  const csv = 'name,phone,email,cargo,empresa\nJoão Silva,5511999990000,joao@email.com,Gerente,Acme\nMaria Santos,5511888880000,,Analista,'
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'template_contatos.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}

const uploadFile = async (file: File) => {
  if (!file.name.endsWith('.csv')) {
    error.value = 'Selecione um arquivo .csv'
    return
  }
  step.value = 'loading'
  error.value = ''
  const fd = new FormData()
  fd.append('file', file)
  try {
    result.value = await api<ImportResult>('/api/contacts/import', {
      method: 'POST',
      body: fd,
    })
    step.value = 'result'
    if (result.value.created > 0) emit('imported')
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao processar o arquivo'
    step.value = 'idle'
  }
}

const onFileInput = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) uploadFile(file)
}

const onDrop = (e: DragEvent) => {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="close"></div>
        <div class="relative bg-surface border border-white/10 w-full max-w-md z-10">
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent"></div>
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent"></div>

          <!-- Header -->
          <div class="px-8 pt-8 pb-6 border-b border-white/5">
            <div class="flex items-start justify-between">
              <div>
                <p class="field-label mb-1">Contatos</p>
                <h2 class="text-xl font-medium text-white tracking-tight">Importar via CSV</h2>
              </div>
              <button @click="close" class="p-1 text-neutral-600 hover:text-neutral-300 transition-colors mt-1">
                <Icon icon="solar:close-circle-bold-duotone" class="text-lg" />
              </button>
            </div>
          </div>

          <!-- Idle state -->
          <div v-if="step === 'idle'" class="px-8 py-6 space-y-6">
            <div class="space-y-2">
              <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-3">Colunas do arquivo</p>
              <div class="flex items-center gap-3">
                <span class="text-[10px] font-mono bg-red-500/10 border border-red-500/20 text-red-400 px-2 py-1 uppercase tracking-wider">name</span>
                <span class="text-xs text-neutral-400">Nome do contato</span>
                <span class="ml-auto text-[9px] font-mono text-red-400 uppercase tracking-widest">obrigatório</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-[10px] font-mono bg-red-500/10 border border-red-500/20 text-red-400 px-2 py-1 uppercase tracking-wider">phone</span>
                <span class="text-xs text-neutral-400">Telefone (ex: 5511999990000)</span>
                <span class="ml-auto text-[9px] font-mono text-red-400 uppercase tracking-widest">obrigatório</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-[10px] font-mono bg-white/5 border border-white/10 text-neutral-400 px-2 py-1 uppercase tracking-wider">email</span>
                <span class="text-xs text-neutral-400">E-mail do contato</span>
                <span class="ml-auto text-[9px] font-mono text-neutral-600 uppercase tracking-widest">opcional</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-[10px] font-mono bg-accent/5 border border-accent/20 text-accent px-2 py-1 uppercase tracking-wider">outras...</span>
                <span class="text-xs text-neutral-400">Salvas como campos personalizados</span>
                <span class="ml-auto text-[9px] font-mono text-neutral-600 uppercase tracking-widest">opcional</span>
              </div>
              
              <div class="space-y-2">
                <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mt-6 mb-2">Cuidados</p>
                <div class="flex items-center gap-3">
                  <span class="text-[10px] font-mono bg-red-500/10 border border-red-500/20 text-red-400 px-2 py-1 uppercase tracking-wider">Atenção!</span>
                  <span class="text-xs text-neutral-400">Importe no máximo ~10.000 linhas</span>
                </div>        
              </div>      
            </div>

            <!-- Download template -->
            <button
              @click="downloadTemplate"
              class="w-full flex items-center gap-2 px-4 py-3 border border-white/5 hover:border-white/10 text-neutral-400 hover:text-white transition-colors"
            >
              <Icon icon="solar:download-minimalistic-bold-duotone" class="text-base shrink-0" />
              <span class="text-xs font-mono">Baixar planilha de exemplo</span>
            </button>

            <!-- Drag & Drop area -->
            <div
              class="border-2 border-dashed transition-colors flex flex-col items-center justify-center py-10 cursor-pointer relative"
              :class="dragOver ? 'border-accent/50 bg-accent/5' : 'border-white/10 hover:border-white/20'"
              @dragover.prevent="dragOver = true"
              @dragleave="dragOver = false"
              @drop.prevent="onDrop"
              @click="($refs.fileInput as HTMLInputElement).click()"
            >
              <input ref="fileInput" type="file" accept=".csv" class="hidden" @change="onFileInput" />
              <Icon icon="solar:upload-minimalistic-bold-duotone" class="text-3xl text-neutral-600 mb-3" />
              <p class="text-sm text-neutral-400 font-mono">Arraste o CSV aqui</p>
              <p class="text-[11px] text-neutral-700 font-mono mt-1">ou clique para selecionar</p>
            </div>

            <p v-if="error" class="text-xs font-mono text-red-400">{{ error }}</p>
          </div>

          <!-- Loading state -->
          <div v-else-if="step === 'loading'" class="px-8 py-16 flex flex-col items-center justify-center">
            <div class="w-8 h-8 border-2 border-accent/20 border-t-accent rounded-full animate-spin mb-4"></div>
            <p class="text-sm font-mono text-neutral-400">Processando arquivo...</p>
          </div>

          <!-- Result state -->
          <div v-else-if="step === 'result' && result" class="px-8 py-6 space-y-4">
            <!-- Resumo -->
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-canvas border border-white/5 px-4 py-4 text-center">
                <p class="text-2xl font-mono text-green-400 font-medium">{{ result.created }}</p>
                <p class="text-[10px] font-mono text-neutral-500 uppercase tracking-widest mt-1">Criados</p>
              </div>
              <div class="bg-canvas border border-white/5 px-4 py-4 text-center">
                <p class="text-2xl font-mono text-neutral-500 font-medium">{{ result.skipped }}</p>
                <p class="text-[10px] font-mono text-neutral-500 uppercase tracking-widest mt-1">Ignorados</p>
              </div>
            </div>

            <p v-if="result.skipped > 0" class="text-[11px] font-mono text-neutral-600">
              Contatos ignorados já existem na base (telefone duplicado).
            </p>

            <!-- Erros por linha -->
            <div v-if="result.errors.length > 0">
              <p class="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mb-2">Linhas com erro</p>
              <div class="max-h-40 overflow-y-auto space-y-1">
                <div
                  v-for="err in result.errors"
                  :key="err.row"
                  class="flex items-center gap-3 px-3 py-2 bg-red-500/5 border border-red-500/10"
                >
                  <span class="text-[10px] font-mono text-red-500 shrink-0">Linha {{ err.row }}</span>
                  <span class="text-[11px] text-neutral-400">{{ err.reason }}</span>
                </div>
              </div>
            </div>

            <!-- Ações -->
            <div class="flex gap-3 pt-2">
              <button
                @click="reset"
                class="flex-1 py-3 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors"
              >
                Importar outro
              </button>
              <button
                @click="close"
                class="flex-1 btn-primary"
              >
                <div class="corner-tl"></div>
                <div class="corner-br"></div>
                <span class="text-white text-xs font-mono uppercase tracking-wider">Fechar</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
