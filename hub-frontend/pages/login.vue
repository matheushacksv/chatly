<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const authStore = useAuthStore()
const router = useRouter()

const form = reactive({ email: '', password: '' })
const error = ref('')
const loading = ref(false)

const submit = async () => {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(form.email, form.password)
    await router.push('/dashboard')
  } catch (e: any) {
    error.value = e?.data?.detail || 'Email ou senha inválidos'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-sm">
    <!-- Header -->
    <div class="mb-10">
      <p class="field-label">Acesse sua conta</p>
      <h1 class="text-3xl font-medium text-white tracking-tight">Login</h1>
    </div>

    <form @submit.prevent="submit" class="space-y-5">
      <!-- Email -->
      <div>
        <label class="field-label">Email</label>
        <div class="input-wrapper">
          <input
            v-model="form.email"
            type="email"
            placeholder="seu@email.com"
            required
            class="input-field"
          />
        </div>
      </div>

      <!-- Senha -->
      <div>
        <label class="field-label">Senha</label>
        <div class="input-wrapper">
          <input
            v-model="form.password"
            type="password"
            placeholder="••••••••"
            required
            class="input-field"
          />
        </div>
      </div>

      <!-- Erro -->
      <p v-if="error" class="text-xs font-mono text-red-400">{{ error }}</p>

      <!-- Submit -->
      <div class="pt-2">
        <button type="submit" :disabled="loading" class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed">
          <div class="corner-tl"></div>
          <div class="corner-br"></div>
          <span class="text-white text-sm font-medium uppercase tracking-wider">
            {{ loading ? 'Entrando...' : 'Entrar' }}
          </span>
        </button>
      </div>
    </form>

    <p class="mt-6 text-center text-xs font-mono text-neutral-500">
      <NuxtLink to="/forgot-password" class="text-accent hover:text-white transition-colors">
        Esqueceu a senha?
      </NuxtLink>
    </p>

    <p class="mt-3 text-center text-xs font-mono text-neutral-500">
      Não tem conta?
      <NuxtLink to="/register" class="text-accent hover:text-white transition-colors ml-1">
        Criar organização
      </NuxtLink>
    </p>
  </div>
</template>
