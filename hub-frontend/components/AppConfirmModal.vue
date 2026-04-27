<script setup lang="ts">
import { Icon } from '@iconify/vue'
const { _state, _accept, _cancel } = useConfirm()
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="_state.open"
        class="fixed inset-0 z-50 flex items-center justify-center px-4"
      >
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="_cancel" />
        <div class="relative bg-surface border border-white/10 w-full max-w-sm p-8 z-10">
          <div class="absolute top-0 left-0 w-4 h-4 border-t border-l border-white/20" />
          <div class="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-white/20" />

          <div class="flex items-start gap-3 mb-6">
            <div
              class="w-8 h-8 shrink-0 flex items-center justify-center border"
              :class="_state.danger ? 'border-red-500/30 bg-red-500/5' : 'border-white/10 bg-white/5'"
            >
              <Icon
                :icon="_state.danger ? 'solar:trash-bin-trash-bold-duotone' : 'solar:question-circle-bold-duotone'"
                class="text-base"
                :class="_state.danger ? 'text-red-400' : 'text-neutral-400'"
              />
            </div>
            <div>
              <p class="text-sm font-medium text-white">{{ _state.title }}</p>
              <p class="text-xs font-mono text-neutral-500 mt-1">{{ _state.message }}</p>
            </div>
          </div>

          <div class="flex gap-3">
            <button
              @click="_cancel"
              class="flex-1 py-2.5 border border-white/10 text-neutral-400 text-xs font-mono uppercase tracking-wider hover:border-white/20 hover:text-white transition-colors"
            >
              Cancelar
            </button>
            <button
              @click="_accept"
              class="flex-1 py-2.5 text-xs font-mono uppercase tracking-wider border transition-colors"
              :class="_state.danger
                ? 'border-red-500/30 text-red-400 hover:bg-red-500/10'
                : 'border-accent/30 text-accent hover:bg-accent/10'"
            >
              {{ _state.confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
