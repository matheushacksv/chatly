<script setup lang="ts">
useHead({
  bodyAttrs: { class: '!overflow-y-auto' },
})
</script>

<template>
  <div class="min-h-screen bg-canvas relative">
    <!-- Grid background -->
    <div class="fixed inset-0 grid-bg pointer-events-none z-0"></div>

    <!-- Beam animations -->
    <div class="beam-border-v fixed left-[25%] pointer-events-none"></div>
    <div class="beam-border-v fixed left-auto right-[25%] pointer-events-none" style="animation-delay: 2.5s"></div>

    <!-- Content -->
    <div class="relative z-10 flex flex-col items-center justify-center min-h-screen px-6 py-16">
      <!-- Logo -->
      <NuxtLink to="/" class="flex items-center gap-2 mb-14">
        <div class="w-3 h-3 bg-accent"></div>
        <span class="text-white text-xs font-mono uppercase tracking-widest">ChatlyAi</span>
      </NuxtLink>

      <!-- Page content -->
      <slot />
    </div>
  </div>
</template>
