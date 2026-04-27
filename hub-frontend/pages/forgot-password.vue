<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const config = useRuntimeConfig()
const email = ref('')
const loading = ref(false)
const sent = ref(false)
const error = ref('')

const submit = async () => {
  error.value = ''
  loading.value = true
  try {
    await $fetch(`${config.public.apiBase}/api/auth/forgot-password`, {
      method: 'POST',
      body: { email: email.value },
    })
    sent.value = true
  } catch {
    error.value = 'Erro ao enviar o email. Tente novamente.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-sm">
    <div class="mb-10">
      <p class="field-label">Recuperar acesso</p>
      <h1 class="text-3xl font-medium text-white tracking-tight">Esqueceu a senha?</h1>
    </div>

    <div v-if="sent" class="bg-green-400/10 border border-green-400/20 p-4 text-xs font-mono text-green-400">
      Link enviado! Verifique seu email e siga as instruções.
    </div>

    <form v-else @submit.prevent="submit" class="space-y-5">
      <div>
        <label class="field-label">Email</label>
        <div class="input-wrapper">
          <input
            v-model="email"
            type="email"
            placeholder="seu@email.com"
            required
            class="input-field"
          />
        </div>
      </div>

      <p v-if="error" class="text-xs font-mono text-red-400">{{ error }}</p>

      <div class="pt-2">
        <button type="submit" :disabled="loading" class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed">
          <div class="corner-tl"></div>
          <div class="corner-br"></div>
          <span class="text-white text-sm font-medium uppercase tracking-wider">
            {{ loading ? 'Enviando...' : 'Enviar link' }}
          </span>
        </button>
      </div>
    </form>

    <p class="mt-8 text-center text-xs font-mono text-neutral-500">
      Lembrou a senha?
      <NuxtLink to="/login" class="text-accent hover:text-white transition-colors ml-1">Voltar ao login</NuxtLink>
    </p>
  </div>
</template>
