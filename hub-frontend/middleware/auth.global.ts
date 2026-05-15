export default defineNuxtRouteMiddleware(async (to) => {
  if (process.server) return

  const authStore = useAuthStore()

  // Carrega tokens do localStorage na primeira navegação
  if (!authStore.accessToken) {
    authStore.loadFromStorage()
  }

  // No domínio da aplicação (app.*) a raiz não é a landing — vai para o painel
  if (to.path === '/' && window.location.host.startsWith('app.')) {
    return navigateTo('/dashboard')
  }

  const isPublicRoute =
    to.path === '/' ||
    to.path === '/privacidade' ||
    to.path === '/cookies' ||
    to.path === '/login' ||
    to.path === '/register' ||
    to.path === '/forgot-password' ||
    to.path === '/reset-password' ||
    to.path.startsWith('/invite/')

  if (!authStore.isAuthenticated && !isPublicRoute) {
    return navigateTo('/login')
  }

  if (authStore.isAuthenticated && (to.path === '/login' || to.path === '/register')) {
    return navigateTo('/dashboard')
  }

  // Mantém o user e suas permissões sempre atualizados
  if (authStore.isAuthenticated && !isPublicRoute) {
    await authStore.fetchMe()
  }
})
