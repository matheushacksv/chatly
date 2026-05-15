<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const route = useRoute()
const authStore = useAuthStore()
const router = useRouter()

const token = route.params.token as string

const form = reactive({
  name: '',
  password: '',
  repeat_password: '',
})
const error = ref('')
const loading = ref(false)

const submit = async () => {
  error.value = ''
  if (form.password !== form.repeat_password) {
    error.value = 'As senhas não coincidem'
    return
  }
  loading.value = true
  try {
    await authStore.acceptInvite({ token, ...form })
    await router.push('/dashboard')
  } catch (e: any) {
    error.value = e?.data?.detail || 'Convite inválido ou expirado'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-sm">
    <!-- Header -->
    <div class="mb-10">
      <p class="field-label">Você foi convidado</p>
      <h1 class="text-3xl font-medium text-white tracking-tight">Criar conta</h1>
    </div>

    <form @submit.prevent="submit" class="space-y-5">
      <!-- Nome -->
      <div>
        <label class="field-label">Seu nome</label>
        <div class="input-wrapper">
          <input v-model="form.name" type="text" placeholder="João Silva" required class="input-field" />
        </div>
      </div>

      <!-- Senha -->
      <div>
        <label class="field-label">Senha</label>
        <div class="input-wrapper">
          <input v-model="form.password" type="password" placeholder="••••••••" required class="input-field" />
        </div>
      </div>

      <!-- Confirmar senha -->
      <div>
        <label class="field-label">Confirmar senha</label>
        <div class="input-wrapper">
          <input v-model="form.repeat_password" type="password" placeholder="••••••••" required class="input-field" />
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
            {{ loading ? 'Entrando...' : 'Aceitar convite' }}
          </span>
        </button>
      </div>
    </form>
  </div>
</template>
