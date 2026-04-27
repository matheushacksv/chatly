<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const authStore = useAuthStore()
const router = useRouter()

const form = reactive({
  org_name: '',
  org_slug: '',
  name: '',
  email: '',
  password: '',
  repeat_password: '',
})
const error = ref('')
const loading = ref(false)

// Gera slug automaticamente a partir do nome da org
watch(() => form.org_name, (val) => {
  form.org_slug = val
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
})

const submit = async () => {
  error.value = ''
  if (form.password !== form.repeat_password) {
    error.value = 'As senhas não coincidem'
    return
  }
  loading.value = true
  try {
    await authStore.register(form)
    await router.push('/')
  } catch (e: any) {
    error.value = e?.data?.detail || 'Erro ao criar conta'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-sm">
    <!-- Header -->
    <div class="mb-10">
      <p class="field-label">Nova organização</p>
      <h1 class="text-3xl font-medium text-white tracking-tight">Criar conta</h1>
    </div>

    <form @submit.prevent="submit" class="space-y-5">
      <!-- Nome da org -->
      <div>
        <label class="field-label">Nome da organização</label>
        <div class="input-wrapper">
          <input v-model="form.org_name" type="text" placeholder="Minha Empresa" required class="input-field" />
        </div>
      </div>

      <!-- Slug -->
      <div>
        <label class="field-label">Slug</label>
        <div class="input-wrapper">
          <input v-model="form.org_slug" type="text" placeholder="minha-empresa" required class="input-field" />
        </div>
        <p class="text-[11px] font-mono text-neutral-600 mt-1.5 pl-4">Identificador único da organização</p>
      </div>

      <!-- Nome do usuário -->
      <div>
        <label class="field-label">Seu nome</label>
        <div class="input-wrapper">
          <input v-model="form.name" type="text" placeholder="João Silva" class="input-field" />
        </div>
      </div>

      <!-- Email -->
      <div>
        <label class="field-label">Email</label>
        <div class="input-wrapper">
          <input v-model="form.email" type="email" placeholder="seu@email.com" required class="input-field" />
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
            {{ loading ? 'Criando...' : 'Criar conta' }}
          </span>
        </button>
      </div>
    </form>

    <p class="mt-8 text-center text-xs font-mono text-neutral-500">
      Já tem conta?
      <NuxtLink to="/login" class="text-accent hover:text-white transition-colors ml-1">
        Fazer login
      </NuxtLink>
    </p>
  </div>
</template>
