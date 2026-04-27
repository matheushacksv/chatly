<script setup lang="ts">
defineProps<{ name: string; color: string }>()
</script>

<template>
  <span
    class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-widest border shrink-0"
    :style="`border-color: ${color}30; background: ${color}12; color: ${color}`"
  >
    <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="`background: ${color}`"></span>
    {{ name }}
  </span>
</template>
