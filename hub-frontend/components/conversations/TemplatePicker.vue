<script setup lang="ts">
import { Icon } from '@iconify/vue'

const props = defineProps<{
  templates: any[]
  query: string     // texto após o "/"
  visible: boolean
}>()

const emit = defineEmits<{
  'select-text':  [template: any]
  'select-media': [template: any]
  close: []
}>()

const cursor = ref(0)

const filtered = computed(() => {
  if (!props.query) return props.templates
  const q = props.query.toLowerCase()
  return props.templates.filter(t =>
    t.title.toLowerCase().includes(q) ||
    (t.shortcut && t.shortcut.toLowerCase().includes(q))
  )
})

// Reset cursor quando a lista muda
watch(filtered, () => { cursor.value = 0 })

const select = (t: any) => {
  if (t.media_type === 'text') emit('select-text', t)
  else emit('select-media', t)
}

const onKeydown = (e: KeyboardEvent) => {
  if (!props.visible) return
  if (e.key === 'ArrowDown') { e.preventDefault(); cursor.value = Math.min(cursor.value + 1, filtered.value.length - 1) }
  if (e.key === 'ArrowUp')   { e.preventDefault(); cursor.value = Math.max(cursor.value - 1, 0) }
  if (e.key === 'Enter')     { e.preventDefault(); if (filtered.value[cursor.value]) select(filtered.value[cursor.value]) }
  if (e.key === 'Escape')    { emit('close') }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

const typeIcons: Record<string, string> = {
  text:     'solar:text-bold-duotone',
  image:    'solar:gallery-bold-duotone',
  document: 'solar:file-bold-duotone',
  audio:    'solar:microphone-bold-duotone',
  sticker:  'solar:sticker-smile-circle-2-bold-duotone',
}
</script>

<template>
  <Transition name="picker">
    <div
      v-if="visible && filtered.length > 0"
      class="absolute bottom-full left-0 right-0 mb-1 bg-surface border border-white/10 max-h-56 overflow-y-auto z-20"
    >
      <div class="px-3 py-1.5 border-b border-white/5 flex items-center justify-between">
        <p class="text-[9px] font-mono uppercase tracking-widest text-neutral-600">Templates — <span class="text-accent">/{{ query }}</span></p>
        <button @click="emit('close')" class="text-neutral-400 hover:text-white transition-colors">
          <Icon icon="solar:close-square-bold" class="text-xs" />
        </button>
      </div>

      <button
        v-for="(t, i) in filtered"
        :key="t.id"
        @click="select(t)"
        @mouseenter="cursor = i"
        class="w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors border-b border-white/[0.03] last:border-0"
        :class="cursor === i ? 'bg-white/[0.05]' : 'hover:bg-white/[0.03]'"
      >
        <!-- Ícone tipo -->
        <Icon
          :icon="typeIcons[t.media_type] || 'solar:text-bold-duotone'"
          class="text-base shrink-0"
          :class="cursor === i ? 'text-accent' : 'text-neutral-600'"
        />

        <!-- Conteúdo -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-white font-medium">{{ t.title }}</span>
            <span v-if="t.shortcut" class="text-[9px] font-mono text-accent/70">/{{ t.shortcut }}</span>
          </div>
          <p v-if="t.content" class="text-[11px] font-mono text-neutral-600 truncate">{{ t.content }}</p>
          <p v-else class="text-[11px] font-mono text-neutral-700 truncate italic">{{ t.media_type }}</p>
        </div>

        <!-- Enter hint quando selecionado -->
        <span v-if="cursor === i" class="text-[9px] font-mono text-neutral-700 shrink-0">↵</span>
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.picker-enter-active, .picker-leave-active { transition: opacity 0.1s, transform 0.1s }
.picker-enter-from, .picker-leave-to { opacity: 0; transform: translateY(4px) }
</style>
