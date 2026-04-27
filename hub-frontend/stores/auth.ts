import { defineStore } from 'pinia'

interface UserPermissions {
  can_view_agents: boolean
  can_create_agents: boolean
  can_edit_agents: boolean
  can_delete_agents: boolean
  can_view_conversations: boolean
  can_delete_conversations: boolean
  can_export_conversations: boolean
}

interface User {
  id: number
  name: string
  email: string
  role: string
  org_name: string
  avatar: string | null
  permissions: UserPermissions
}

interface OrgItem {
  id: number
  name: string
  slug: string
  role: string
  is_active: boolean
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  myOrgs: OrgItem[]
  _userFetchedAt: number | null
}

// Recarrega permissões a cada 60 segundos no máximo
const FETCH_ME_TTL_MS = 60_000

// Mutex para evitar múltiplas chamadas simultâneas de refresh (fora do Pinia para não quebrar reatividade)
let _refreshPromise: Promise<boolean> | null = null

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    accessToken: null,
    refreshToken: null,
    user: null,
    myOrgs: [],
    _userFetchedAt: null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },

  actions: {
    loadFromStorage() {
      if (!process.client) return
      this.accessToken = localStorage.getItem('access_token')
      this.refreshToken = localStorage.getItem('refresh_token')
    },

    _saveToStorage() {
      if (!process.client) return
      if (this.accessToken) localStorage.setItem('access_token', this.accessToken)
      if (this.refreshToken) localStorage.setItem('refresh_token', this.refreshToken)
    },

    _setTokens(access: string, refresh: string) {
      this.accessToken = access
      this.refreshToken = refresh
      this._saveToStorage()
    },

    async login(email: string, password: string) {
      const config = useRuntimeConfig()
      const data = await $fetch<{ access: string; refresh: string }>(
        `${config.public.apiBase}/api/auth/login`,
        { method: 'POST', body: { email, password } }
      )
      this._setTokens(data.access, data.refresh)
      await this.fetchMe(true)
      await this.fetchMyOrgs()
    },

    async register(payload: {
      org_name: string
      org_slug: string
      name: string
      email: string
      password: string
      repeat_password: string
    }) {
      const config = useRuntimeConfig()
      const data = await $fetch<{ access: string; refresh: string }>(
        `${config.public.apiBase}/api/auth/register`,
        { method: 'POST', body: payload }
      )
      this._setTokens(data.access, data.refresh)
      await this.fetchMe(true)
      await this.fetchMyOrgs()
    },

    async acceptInvite(payload: {
      token: string
      name: string
      password: string
      repeat_password: string
    }) {
      const config = useRuntimeConfig()
      const data = await $fetch<{ access: string; refresh: string }>(
        `${config.public.apiBase}/api/auth/invite/accept`,
        { method: 'POST', body: payload }
      )
      this._setTokens(data.access, data.refresh)
      await this.fetchMe(true)
      await this.fetchMyOrgs()
    },

    // force=true ignora o TTL (usado no login/register)
    async fetchMe(force = false) {
      if (!this.accessToken) return

      const now = Date.now()
      if (!force && this._userFetchedAt && (now - this._userFetchedAt) < FETCH_ME_TTL_MS) return

      const config = useRuntimeConfig()

      const doFetch = async () => {
        const user = await $fetch<User>(`${config.public.apiBase}/api/auth/me`, {
          headers: { Authorization: `Bearer ${this.accessToken}` },
        })
        this.user = user
        this._userFetchedAt = Date.now()
        if (this.myOrgs.length === 0) await this.fetchMyOrgs()
      }

      try {
        await doFetch()
      } catch (e: any) {
        if (e?.status === 401) {
          // Tenta renovar o token antes de fazer logout
          const refreshed = await this.refresh()
          if (refreshed) {
            try { await doFetch() } catch { this.logout() }
          }
          // refresh() já chama logout() se falhar
        }
      }
    },

    // Retorna true se conseguiu renovar, false se precisa fazer login novamente
    async refresh(): Promise<boolean> {
      if (!this.refreshToken) { this.logout(); return false }

      // Evita múltiplas chamadas simultâneas de refresh
      if (_refreshPromise) return _refreshPromise

      _refreshPromise = (async () => {
        try {
          const config = useRuntimeConfig()
          const data = await $fetch<{ access: string; refresh: string }>(
            `${config.public.apiBase}/api/auth/refresh`,
            { method: 'POST', body: { refresh: this.refreshToken } }
          )
          this._setTokens(data.access, data.refresh)
          this._userFetchedAt = null  // força re-fetch do user na próxima navegação
          return true
        } catch {
          this.logout()
          return false
        } finally {
          _refreshPromise = null
        }
      })()

      return _refreshPromise
    },

    async fetchMyOrgs() {
      if (!this.accessToken) return
      const config = useRuntimeConfig()
      try {
        this.myOrgs = await $fetch<OrgItem[]>(`${config.public.apiBase}/api/auth/my-orgs`, {
          headers: { Authorization: `Bearer ${this.accessToken}` },
        })
      } catch {}
    },

    async switchOrg(orgId: number) {
      const config = useRuntimeConfig()
      const data = await $fetch<{ access: string; refresh: string }>(
        `${config.public.apiBase}/api/auth/switch-org`,
        {
          method: 'POST',
          body: { org_id: orgId },
          headers: { Authorization: `Bearer ${this.accessToken}` },
        }
      )
      this._setTokens(data.access, data.refresh)
      this._userFetchedAt = null
      await this.fetchMe(true)
      await this.fetchMyOrgs()
      window.location.href = '/'
    },

    logout() {
      this.accessToken = null
      this.refreshToken = null
      this.user = null
      this.myOrgs = []
      this._userFetchedAt = null
      if (process.client) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      }
    },
  },
})
