<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const config = useRuntimeConfig()
const route = useRoute()

const uid = route.query.uid as string
const token = route.query.token as string

const form = reactive({ password: '', repeat_password: '' })
const loading = ref(false)
const success = ref(false)
const error = ref('')

const submit = async () => {
  error.value = ''
  loading.value = true
  try {
    await $fetch(`${config.public.apiBase}/api/auth/reset-password`, {
      method: 'POST',
      body: { uid, token, password: form.password, repeat_password: form.repeat_password },
    })
    success.value = true
  } catch (e: any) {
    error.value = e?.data?.detail || 'Token inválido ou expirado.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-sm">
    <div class="mb-10">
      <p class="field-label">Nova senha</p>
      <h1 class="text-3xl font-medium text-white tracking-tight">Redefinir senha</h1>
    </div>

    <div v-if="!uid || !token" class="text-xs font-mono text-red-400">
      Link inválido. Solicite um novo link de recuperação.
    </div>

    <div v-else-if="success" class="space-y-5">
      <p class="bg-green-400/10 border border-green-400/20 p-4 text-xs font-mono text-green-400">
        Senha redefinida com sucesso!
      </p>
      <NuxtLink to="/login" class="btn-primary inline-flex">
        <div class="corner-tl"></div>
        <div class="corner-br"></div>
        <span class="text-white text-sm font-medium uppercase tracking-wider">Fazer login</span>
      </NuxtLink>
    </div>

    <form v-else @submit.prevent="submit" class="space-y-5">
      <div>
        <label class="field-label">Nova senha</label>
        <div class="input-wrapper">
          <input
            v-model="form.password"
            type="password"
            placeholder="Mínimo 8 caracteres"
            required
            minlength="8"
            class="input-field"
          />
        </div>
      </div>

      <div>
        <label class="field-label">Confirmar senha</label>
        <div class="input-wrapper">
          <input
            v-model="form.repeat_password"
            type="password"
            placeholder="Repita a senha"
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
            {{ loading ? 'Salvando...' : 'Redefinir senha' }}
          </span>
        </button>
      </div>
    </form>

    <p class="mt-8 text-center text-xs font-mono text-neutral-500">
      <NuxtLink to="/login" class="text-accent hover:text-white transition-colors">Voltar ao login</NuxtLink>
    </p>
  </div>
</template>
