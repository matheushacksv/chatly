<script setup lang="ts">
import { Icon } from '@iconify/vue'

const authStore = useAuthStore()
const route = useRoute()
const { isOpen, close, isCollapsed, toggleCollapsed } = useSidebar()
const { total: totalUnread } = useUnread()
const { hiddenPaths, orderedAllItems } = useSidebarNav()

const closeOnMobile = () => {
  if (window.innerWidth < 768) close()
}

const isOwnerOrAdmin = computed(() => ['owner', 'admin'].includes(authStore.user?.role ?? ''))
const hasAnyAgentPermission = computed(() =>
  isOwnerOrAdmin.value ||
  authStore.user?.permissions?.can_view_agents ||
  authStore.user?.permissions?.can_create_agents ||
  authStore.user?.permissions?.can_edit_agents ||
  authStore.user?.permissions?.can_delete_agents
)

const navItems = computed(() =>
  orderedAllItems.value.filter((item: any) => {
    if (item.ownerAdminOnly) return isOwnerOrAdmin.value
    if (item.requireAgentPermission) return hasAnyAgentPermission.value
    return true
  })
)

const visibleItems = computed(() => navItems.value.filter((i: any) => !hiddenPaths.value.includes(i.to)))
const overflowItems = computed(() => navItems.value.filter((i: any) => hiddenPaths.value.includes(i.to)))

const showOverflow = ref(false)
const overflowRef = ref<HTMLElement>()

const closeOverflow = (e: MouseEvent) => {
  if (overflowRef.value && !overflowRef.value.contains(e.target as Node)) showOverflow.value = false
}
onMounted(() => document.addEventListener('click', closeOverflow))
onUnmounted(() => document.removeEventListener('click', closeOverflow))

watch(() => route.path, () => { showOverflow.value = false })

const isActive = (to: string) => {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}

const handleLogout = () => {
  authStore.logout()
  navigateTo('/login')
}

const orgOpen = ref(false)
const orgSwitcherRef = ref<HTMLElement>()

const closeOrgSwitcher = (e: MouseEvent) => {
  if (orgSwitcherRef.value && !orgSwitcherRef.value.contains(e.target as Node)) orgOpen.value = false
}
onMounted(() => document.addEventListener('click', closeOrgSwitcher))
onUnmounted(() => document.removeEventListener('click', closeOrgSwitcher))
</script>

<template>
  <!-- Backdrop mobile -->
  <Transition name="fade">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-30 bg-black/60 md:hidden"
      @click="close"
    />
  </Transition>

  <aside
    class="bg-surface border-r border-white/5 flex flex-col fixed inset-y-0 left-0 z-40 transition-all duration-200"
    :class="[
      isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
      isCollapsed ? 'w-14' : 'w-56'
    ]"
  >
    <!-- Logo -->
    <div class="border-b border-white/5 flex items-center" :class="isCollapsed ? 'px-0 py-5 justify-center' : 'px-5 py-5'">
      <NuxtLink to="/" class="flex items-center gap-2.5">
        <div class="w-3 h-3 bg-accent shrink-0"></div>
        <span v-if="!isCollapsed" class="text-white text-xs font-mono uppercase tracking-widest">ChatlyAi</span>
      </NuxtLink>
      <!-- Botão collapse — apenas desktop -->
      <button
        @click="toggleCollapsed"
        class="hidden md:flex ml-auto text-neutral-500 hover:text-neutral-200 transition-colors"
        :class="isCollapsed ? 'mx-auto' : 'ml-auto'"
        :title="isCollapsed ? 'Expandir menu' : 'Recolher menu'"
      >
        <Icon :icon="isCollapsed ? 'solar:arrow-right-bold-duotone' : 'solar:arrow-left-bold-duotone'" class="text-sm" />
      </button>
    </div>

    <!-- Nav -->
    <nav class="flex-1 px-2 py-4 space-y-0.5 overflow-visible">
      <NuxtLink
        v-for="item in visibleItems"
        :key="item.to"
        :to="item.to"
        @click="closeOnMobile"
        class="flex items-center gap-3 py-2.5 text-sm transition-all duration-200 relative"
        :class="[
          isCollapsed ? 'px-0 justify-center' : 'px-3',
          isActive(item.to)
            ? 'text-accent bg-accent/5'
            : 'text-neutral-400 hover:text-neutral-200 hover:bg-white/5'
        ]"
        :title="isCollapsed ? item.label : undefined"
      >
        <div v-if="isActive(item.to)" class="absolute left-0 inset-y-0 w-0.5 bg-accent"></div>
        <Icon :icon="item.icon" class="text-lg shrink-0" />
        <span v-if="!isCollapsed" class="font-mono text-xs uppercase tracking-wider flex-1">{{ item.label }}</span>
        <span
          v-if="item.to === '/conversations' && totalUnread > 0"
          class="text-[9px] font-mono bg-accent text-white px-1.5 py-0.5 rounded-full leading-none shrink-0"
          :class="isCollapsed ? 'absolute top-1 right-1' : ''"
        >
          {{ totalUnread > 99 ? '99+' : totalUnread }}
        </span>
      </NuxtLink>

      <!-- Botão "Mais" com submenu -->
      <div v-if="overflowItems.length > 0" ref="overflowRef" class="relative">
        <button
          @click.stop="showOverflow = !showOverflow"
          class="w-full flex items-center gap-3 py-2.5 text-sm transition-all duration-200"
          :class="[
            isCollapsed ? 'px-0 justify-center' : 'px-3',
            showOverflow ? 'text-accent bg-accent/5' : 'text-neutral-400 hover:text-neutral-200 hover:bg-white/5'
          ]"
          :title="isCollapsed ? 'Mais' : undefined"
        >
          <Icon icon="solar:menu-dots-bold-duotone" class="text-lg shrink-0" />
          <span v-if="!isCollapsed" class="font-mono text-xs uppercase tracking-wider flex-1 text-left">Mais</span>
        </button>

        <div
          v-if="showOverflow"
          class="absolute bg-surface border border-white/10 shadow-xl z-50 w-48 py-1"
          :style="isCollapsed ? 'left: calc(100% + 8px); bottom: 0' : 'left: 0; bottom: calc(100% + 4px)'"
        >
          <NuxtLink
            v-for="item in overflowItems"
            :key="item.to"
            :to="item.to"
            @click="showOverflow = false; closeOnMobile()"
            class="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors relative"
            :class="isActive(item.to) ? 'text-accent bg-accent/5' : 'text-neutral-400 hover:text-neutral-200 hover:bg-white/5'"
          >
            <div v-if="isActive(item.to)" class="absolute left-0 inset-y-0 w-0.5 bg-accent"></div>
            <Icon :icon="item.icon" class="text-base shrink-0" />
            <span class="font-mono text-xs uppercase tracking-wider flex-1">{{ item.label }}</span>
            <span
              v-if="item.to === '/conversations' && totalUnread > 0"
              class="text-[9px] font-mono bg-accent text-white px-1.5 py-0.5 rounded-full leading-none shrink-0"
            >{{ totalUnread > 99 ? '99+' : totalUnread }}</span>
          </NuxtLink>
        </div>
      </div>
    </nav>

    <!-- Org switcher -->
    <div
      v-if="authStore.myOrgs.length > 1 && !isCollapsed"
      ref="orgSwitcherRef"
      class="relative px-4 py-3 border-t border-white/5"
    >
      <button
        @click.stop="orgOpen = !orgOpen"
        class="w-full flex items-center justify-between gap-2 text-left"
      >
        <div class="min-w-0">
          <p class="text-[9px] font-mono text-neutral-600 uppercase tracking-widest mb-0.5">Organização</p>
          <p class="text-xs text-white truncate">{{ authStore.user?.org_name }}</p>
        </div>
        <Icon icon="solar:alt-arrow-down-bold-duotone" class="text-neutral-500 shrink-0 text-sm transition-transform" :class="orgOpen ? 'rotate-180' : ''" />
      </button>
      <div
        v-if="orgOpen"
        class="absolute bottom-full left-4 right-4 bg-surface border border-white/10 shadow-xl z-50 mb-1"
      >
        <button
          v-for="org in authStore.myOrgs"
          :key="org.id"
          @click="authStore.switchOrg(org.id); orgOpen = false"
          class="w-full flex items-center justify-between px-3 py-2.5 text-xs hover:bg-white/5 transition-colors"
          :class="org.is_active ? 'text-accent' : 'text-neutral-400'"
        >
          <span class="truncate">{{ org.name }}</span>
          <Icon v-if="org.is_active" icon="solar:check-circle-bold" class="shrink-0 text-sm" />
        </button>
      </div>
    </div>

    <!-- User -->
    <div class="py-4 border-t border-white/5" :class="isCollapsed ? 'px-0' : 'px-4'">
      <div class="flex items-center" :class="isCollapsed ? 'flex-col gap-2' : 'gap-2.5'">
        <div class="w-7 h-7 shrink-0 border border-white/10 overflow-hidden">
          <img
            v-if="authStore.user?.avatar"
            :src="authStore.user.avatar"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full bg-neutral-900 flex items-center justify-center">
            <span class="text-[10px] font-mono text-neutral-400 uppercase">
              {{ (authStore.user?.name?.[0] || authStore.user?.email?.[0] || '?').toUpperCase() }}
            </span>
          </div>
        </div>
        <div v-if="!isCollapsed" class="flex-1 min-w-0">
          <p class="text-xs text-white truncate">{{ authStore.user?.name || authStore.user?.email }}</p>
          <p class="text-[10px] font-mono text-neutral-600 uppercase tracking-wider">{{ authStore.user?.role }}</p>
        </div>
        <button
          @click="handleLogout"
          class="text-neutral-400 hover:text-accent transition-colors shrink-0"
          title="Sair"
        >
          <Icon icon="solar:logout-2-bold-duotone" class="text-base" />
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
