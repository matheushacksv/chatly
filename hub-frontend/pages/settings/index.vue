<script setup lang="ts">
import { Icon } from '@iconify/vue'

const api = useApi()
const authStore = useAuthStore()
const { hiddenPaths, setHidden, navOrder, setOrder, orderedAllItems } = useSidebarNav()

const isOwnerOrAdmin = computed(() => ['owner', 'admin'].includes(authStore.user?.role ?? ''))
const hasAnyAgentPermission = computed(() =>
  isOwnerOrAdmin.value ||
  authStore.user?.permissions?.can_view_agents ||
  authStore.user?.permissions?.can_create_agents ||
  authStore.user?.permissions?.can_edit_agents ||
  authStore.user?.permissions?.can_delete_agents
)

const configurableItems = computed(() =>
  orderedAllItems.value.filter((i: any) => {
    if (i.ownerAdminOnly) return isOwnerOrAdmin.value
    if (i.requireAgentPermission) return hasAnyAgentPermission.value
    return true
  })
)

const toggleNavItem = (to: string) => {
  const current = [...hiddenPaths.value]
  const idx = current.indexOf(to)
  if (idx === -1) current.push(to)
  else current.splice(idx, 1)
  setHidden(current)
}

// ---- Drag-and-drop de ordenação ----
const dragIndex = ref<number | null>(null)
const overIndex = ref<number | null>(null)

const onDragStart = (idx: number) => { dragIndex.value = idx }
const onDragOver = (idx: number) => { overIndex.value = idx }
const onDragEnd = () => {
  if (dragIndex.value !== null && overIndex.value !== null && dragIndex.value !== overIndex.value) {
    const items = [...configurableItems.value]
    const [moved] = items.splice(dragIndex.value, 1)
    items.splice(overIndex.value, 0, moved)
    // Reconstrói ordem completa: itens configuráveis na nova ordem + demais no final
    const configurablePaths = new Set(configurableItems.value.map(i => i.to))
    const nonConfigurablePaths = navOrder.value.filter(p => !configurablePaths.has(p))
    setOrder([...items.map(i => i.to), ...nonConfigurablePaths])
  }
  dragIndex.value = null
  overIndex.value = null
}

const tab = ref<'profile' | 'organization' | 'appearance' | 'navigation'>('profile')

// ---- Tema ----
const { theme, accentHex, presets, setTheme, setAccent } = useTheme()

// ---- Avatar ----
const avatarInput = ref<HTMLInputElement>()
const avatarLoading = ref(false)

const uploadAvatar = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  avatarLoading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const updated = await api<any>('/api/auth/avatar', { method: 'PATCH', body: fd })
    authStore.user = { ...authStore.user!, avatar: updated.avatar }
  } catch {}
  finally { avatarLoading.value = false }
}

// ---- Perfil ----
const profileForm = reactive({ name: '', current_password: '', new_password: '', repeat_password: '' })
const profileLoading = ref(false)
const profileError = ref('')
const profileSuccess = ref(false)

watch(() => authStore.user, (u) => {
  if (u) profileForm.name = u.name
}, { immediate: true })

const saveProfile = async () => {
  profileError.value = ''
  profileSuccess.value = false

  if (profileForm.new_password && profileForm.new_password !== profileForm.repeat_password) {
    profileError.value = 'As senhas não coincidem'
    return
  }

  profileLoading.value = true
  try {
    const body: any = {}
    if (profileForm.name.trim()) body.name = profileForm.name.trim()
    if (profileForm.new_password) {
      body.current_password = profileForm.current_password
      body.new_password = profileForm.new_password
    }

    const updated = await api<any>('/api/auth/me', { method: 'PUT', body })
    authStore.user = { ...authStore.user!, ...updated }
    profileForm.current_password = ''
    profileForm.new_password = ''
    profileForm.repeat_password = ''
    profileSuccess.value = true
    setTimeout(() => profileSuccess.value = false, 3000)
  } catch (e: any) {
    profileError.value = e?.data?.detail || 'Erro ao salvar'
  } finally {
    profileLoading.value = false
  }
}

// ---- Organização ----
const orgForm = reactive({ name: '' })
const orgLoading = ref(false)
const orgError = ref('')
const orgSuccess = ref(false)
const isOwner = computed(() => authStore.user?.role?.toLowerCase() === 'owner')

watch(() => authStore.user, (u) => {
  if (u) orgForm.name = u.org_name
}, { immediate: true })

const saveOrg = async () => {
  orgError.value = ''
  orgSuccess.value = false
  orgLoading.value = true
  try {
    const updated = await api<any>('/api/org/settings', {
      method: 'PATCH',
      body: { name: orgForm.name.trim() },
    })
    authStore.user = { ...authStore.user!, org_name: updated.name }
    orgSuccess.value = true
    setTimeout(() => orgSuccess.value = false, 3000)
  } catch (e: any) {
    orgError.value = e?.data?.detail || 'Erro ao salvar'
  } finally {
    orgLoading.value = false
  }
}
</script>

<template>
  <div class="p-4 md:p-8 max-w-4xl">
    <!-- Header -->
    <div class="mb-8">
      <p class="field-label mb-0.5">Conta</p>
      <h1 class="text-2xl font-medium text-white tracking-tight">Configurações</h1>
    </div>

    <!-- Tabs -->
    <div class="flex border-b border-white/5 mb-8">
      <button
        @click="tab = 'profile'"
        class="pb-3 text-[10px] font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors whitespace-nowrap"
        :class="tab === 'profile' ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
        style="margin-right: 40px"
      >
        Meu perfil
      </button>
      <button
        @click="tab = 'organization'"
        class="pb-3 text-[10px] font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors whitespace-nowrap"
        :class="tab === 'organization' ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
        style="margin-right: 40px"
      >
        Organização
      </button>
      <button
        @click="tab = 'appearance'"
        class="pb-3 text-[10px] font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors whitespace-nowrap"
        :class="tab === 'appearance' ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
        style="margin-right: 40px"
      >
        Aparência
      </button>
      <button
        @click="tab = 'navigation'"
        class="pb-3 text-[10px] font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors whitespace-nowrap"
        :class="tab === 'navigation' ? 'text-accent border-accent' : 'text-neutral-600 border-transparent hover:text-neutral-400'"
      >
        Navegação
      </button>
    </div>

    <!-- ======== PERFIL ======== -->
    <div v-if="tab === 'profile'">
      <form @submit.prevent="saveProfile" class="space-y-6">

        <!-- Info atual -->
        <div class="flex items-center gap-4 p-5 bg-surface border border-white/5">
          <!-- Avatar clicável -->
          <input ref="avatarInput" type="file" accept="image/*" class="hidden" @change="uploadAvatar" />
          <button
            type="button"
            @click="avatarInput?.click()"
            class="relative w-12 h-12 shrink-0 group"
            title="Alterar foto"
          >
            <!-- Avatar ou iniciais -->
            <img
              v-if="authStore.user?.avatar"
              :src="authStore.user.avatar"
              class="w-full h-full object-cover border border-white/10"
            />
            <div
              v-else
              class="w-full h-full bg-neutral-900 border border-white/10 flex items-center justify-center"
            >
              <span class="text-lg font-mono text-neutral-300 uppercase leading-none">
                {{ authStore.user?.name?.[0] ?? authStore.user?.email?.[0] ?? '?' }}
              </span>
            </div>
            <!-- Overlay hover -->
            <div class="absolute inset-0 bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <Icon v-if="!avatarLoading" icon="solar:camera-bold-duotone" class="text-white text-base" />
              <Icon v-else icon="solar:refresh-bold-duotone" class="text-white text-base animate-spin" />
            </div>
          </button>

          <div>
            <p class="text-sm text-white font-medium">{{ authStore.user?.name }}</p>
            <p class="text-xs font-mono text-neutral-600">{{ authStore.user?.email }}</p>
            <span class="text-[9px] font-mono uppercase tracking-widest px-1.5 py-0.5 mt-1 inline-block"
              :class="{
                'text-accent bg-accent/10': authStore.user?.role === 'owner',
                'text-blue-400 bg-blue-400/10': authStore.user?.role === 'admin',
                'text-neutral-400 bg-white/5': authStore.user?.role === 'member',
              }"
            >{{ authStore.user?.role }}</span>
          </div>
        </div>

        <!-- Nome -->
        <div>
          <label class="field-label">Nome</label>
          <div class="input-wrapper mt-1">
            <input v-model="profileForm.name" type="text" placeholder="Seu nome" class="input-field" />
          </div>
        </div>

        <hr class="border-white/5" />

        <!-- Trocar senha -->
        <div>
          <p class="text-xs font-mono text-neutral-500 uppercase tracking-widest mb-4">Trocar senha</p>
          <div class="space-y-3">
            <div>
              <label class="field-label">Senha atual</label>
              <div class="input-wrapper mt-1">
                <input v-model="profileForm.current_password" type="password" placeholder="••••••••" class="input-field" />
              </div>
            </div>
            <div>
              <label class="field-label">Nova senha</label>
              <div class="input-wrapper mt-1">
                <input v-model="profileForm.new_password" type="password" placeholder="••••••••" class="input-field" />
              </div>
            </div>
            <div>
              <label class="field-label">Confirmar nova senha</label>
              <div class="input-wrapper mt-1">
                <input v-model="profileForm.repeat_password" type="password" placeholder="••••••••" class="input-field" />
              </div>
            </div>
          </div>
        </div>

        <!-- Feedback -->
        <p v-if="profileError" class="text-xs font-mono text-red-400">{{ profileError }}</p>
        <div v-if="profileSuccess" class="flex items-center gap-2 text-xs font-mono text-green-400">
          <Icon icon="solar:check-circle-bold-duotone" />
          Salvo com sucesso
        </div>

        <div class="flex justify-end pt-2">
          <button type="submit" :disabled="profileLoading" class="btn-primary px-6 py-2.5 disabled:opacity-50">
            <div class="corner-tl"></div>
            <div class="corner-br"></div>
            <span class="text-white text-xs font-mono uppercase tracking-wider">
              {{ profileLoading ? 'Salvando...' : 'Salvar' }}
            </span>
          </button>
        </div>
      </form>
    </div>

    <!-- ======== ORGANIZAÇÃO ======== -->
    <div v-if="tab === 'organization'">

      <div v-if="!isOwner" class="flex items-center gap-3 p-4 border border-white/5 bg-surface text-xs font-mono text-neutral-500 mb-6">
        <Icon icon="solar:lock-bold-duotone" class="text-base shrink-0" />
        Apenas o owner pode editar as configurações da organização.
      </div>

      <form @submit.prevent="saveOrg" class="space-y-6">
        <div>
          <label class="field-label">Nome da organização</label>
          <div class="input-wrapper mt-1">
            <input
              v-model="orgForm.name"
              type="text"
              placeholder="Minha Empresa"
              :disabled="!isOwner"
              class="input-field disabled:opacity-40"
            />
          </div>
        </div>

        <div>
          <label class="field-label">Slug</label>
          <div class="input-wrapper mt-1 opacity-40">
            <input
              :value="authStore.user?.org_name?.toLowerCase().replace(/\s+/g, '-')"
              type="text"
              disabled
              class="input-field cursor-not-allowed"
            />
          </div>
          <p class="text-[10px] font-mono text-neutral-700 mt-1 pl-4">O slug não pode ser alterado após o cadastro</p>
        </div>

        <!-- Feedback -->
        <p v-if="orgError" class="text-xs font-mono text-red-400">{{ orgError }}</p>
        <div v-if="orgSuccess" class="flex items-center gap-2 text-xs font-mono text-green-400">
          <Icon icon="solar:check-circle-bold-duotone" />
          Salvo com sucesso
        </div>

        <div v-if="isOwner" class="flex justify-end pt-2">
          <button type="submit" :disabled="orgLoading" class="btn-primary px-6 py-2.5 disabled:opacity-50">
            <div class="corner-tl"></div>
            <div class="corner-br"></div>
            <span class="text-white text-xs font-mono uppercase tracking-wider">
              {{ orgLoading ? 'Salvando...' : 'Salvar' }}
            </span>
          </button>
        </div>
      </form>
    </div>

    <!-- ======== APARÊNCIA ======== -->
    <div v-if="tab === 'appearance'" class="space-y-8">

      <!-- Tema -->
      <div>
        <p class="text-xs font-mono text-neutral-500 uppercase tracking-widest mb-4">Tema</p>
        <div class="grid grid-cols-2 gap-3">
          <!-- Dark -->
          <button
            type="button"
            @click="setTheme('dark')"
            class="relative p-4 border transition-all flex flex-col items-center gap-3"
            :class="theme === 'dark' ? 'border-accent bg-accent/5' : 'border-white/5 hover:border-white/10'"
          >
            <div class="w-full h-16 bg-[#050505] border border-white/10 flex items-end p-1.5 gap-1">
              <div class="w-8 h-full bg-[#0A0A0A] border border-white/5"></div>
              <div class="flex-1 h-full bg-[#0d0d0d] border border-white/5"></div>
            </div>
            <div class="flex items-center gap-2">
              <Icon icon="solar:moon-bold-duotone" class="text-sm" :class="theme === 'dark' ? 'text-accent' : 'text-neutral-500'" />
              <span class="text-xs font-mono uppercase tracking-wider" :class="theme === 'dark' ? 'text-accent' : 'text-neutral-500'">Escuro</span>
            </div>
            <div v-if="theme === 'dark'" class="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-accent"></div>
          </button>

          <!-- Light -->
          <button
            type="button"
            @click="setTheme('light')"
            class="relative p-4 border transition-all flex flex-col items-center gap-3"
            :class="theme === 'light' ? 'border-accent bg-accent/5' : 'border-white/5 hover:border-white/10'"
          >
            <div class="w-full h-16 bg-[#f0f0f0] border border-black/10 flex items-end p-1.5 gap-1">
              <div class="w-8 h-full bg-white border border-black/8"></div>
              <div class="flex-1 h-full bg-[#f8f8f8] border border-black/8"></div>
            </div>
            <div class="flex items-center gap-2">
              <Icon icon="solar:sun-bold-duotone" class="text-sm" :class="theme === 'light' ? 'text-accent' : 'text-neutral-500'" />
              <span class="text-xs font-mono uppercase tracking-wider" :class="theme === 'light' ? 'text-accent' : 'text-neutral-500'">Claro</span>
            </div>
            <div v-if="theme === 'light'" class="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-accent"></div>
          </button>
        </div>
      </div>

      <hr class="border-white/5" />

      <!-- Cor de destaque -->
      <div>
        <p class="text-xs font-mono text-neutral-500 uppercase tracking-widest mb-4">Cor de destaque</p>

        <!-- Presets -->
        <div class="flex flex-wrap gap-2.5 mb-4">
          <button
            v-for="preset in presets"
            :key="preset.hex"
            type="button"
            @click="setAccent(preset.hex)"
            :title="preset.label"
            class="w-7 h-7 border-2 transition-all"
            :style="{ backgroundColor: preset.hex, borderColor: accentHex === preset.hex ? preset.hex : 'transparent' }"
            :class="accentHex === preset.hex ? 'scale-110 shadow-lg' : 'opacity-70 hover:opacity-100 hover:scale-105'"
          ></button>
        </div>

        <!-- Color picker customizado -->
        <div class="flex items-center gap-3">
          <label class="relative cursor-pointer">
            <input
              type="color"
              :value="accentHex"
              @input="setAccent(($event.target as HTMLInputElement).value)"
              class="sr-only"
            />
            <div
              class="w-8 h-8 border-2 border-white/10 cursor-pointer hover:border-white/30 transition-colors"
              :style="{ backgroundColor: accentHex }"
              title="Escolher cor personalizada"
            ></div>
          </label>
          <div class="input-wrapper flex-1" style="border-radius: 4px; padding: 0.4rem 0.75rem;">
            <span class="text-xs font-mono text-neutral-500 mr-2">#</span>
            <input
              :value="accentHex.replace('#', '')"
              @input="e => { const v = (e.target as HTMLInputElement).value; if (/^[0-9a-fA-F]{6}$/.test(v)) setAccent('#' + v) }"
              maxlength="6"
              placeholder="F97316"
              class="input-field text-xs"
              style="font-family: ui-monospace, monospace;"
            />
          </div>
        </div>

        <!-- Preview -->
        <div class="mt-4 p-3 border border-white/5 flex items-center gap-3">
          <div class="w-2 h-2 rounded-full bg-accent"></div>
          <span class="text-xs font-mono text-neutral-500 flex-1">Preview</span>
          <button type="button" class="text-[10px] font-mono uppercase tracking-wider text-accent border border-accent px-2 py-1 hover:bg-accent/10 transition-colors">
            Botão
          </button>
        </div>
      </div>

    </div>

    <!-- ======== NAVEGAÇÃO ======== -->
    <div v-if="tab === 'navigation'" class="space-y-6">
      <div>
        <p class="text-xs font-mono text-neutral-500 uppercase tracking-widest mb-1">Menu lateral</p>
        <p class="text-[10px] font-mono text-neutral-700 mb-4">Arraste para reordenar. Itens desmarcados ficam agrupados em "···" no sidebar.</p>
        <div class="space-y-1">
          <div
            v-for="(item, idx) in configurableItems"
            :key="item.to"
            draggable="true"
            @dragstart="onDragStart(idx)"
            @dragover.prevent="onDragOver(idx)"
            @dragend="onDragEnd"
            class="flex items-center gap-3 p-3 border transition-colors select-none cursor-grab active:cursor-grabbing"
            :class="overIndex === idx && dragIndex !== idx
              ? 'border-accent/40 bg-accent/5'
              : 'border-white/5 hover:bg-white/[0.02]'"
          >
            <Icon icon="solar:sort-by-time-bold-duotone" class="text-sm text-neutral-700 shrink-0" />
            <div
              class="w-4 h-4 border shrink-0 flex items-center justify-center transition-colors cursor-pointer"
              :class="!hiddenPaths.includes(item.to) ? 'border-accent bg-accent/20' : 'border-white/10'"
              @click="toggleNavItem(item.to)"
            >
              <Icon v-if="!hiddenPaths.includes(item.to)" icon="solar:check-bold" class="text-accent text-[10px]" />
            </div>
            <Icon :icon="item.icon" class="text-base shrink-0" :class="!hiddenPaths.includes(item.to) ? 'text-neutral-300' : 'text-neutral-600'" />
            <span class="text-xs font-mono flex-1" :class="!hiddenPaths.includes(item.to) ? 'text-neutral-300' : 'text-neutral-600'">
              {{ item.label }}
            </span>
            <span
              class="text-[9px] font-mono uppercase tracking-widest px-1.5 py-0.5"
              :class="!hiddenPaths.includes(item.to) ? 'text-accent bg-accent/10' : 'text-neutral-700 bg-white/5'"
            >
              {{ !hiddenPaths.includes(item.to) ? 'visível' : '···' }}
            </span>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>
