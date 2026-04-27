export const useApi = () => {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  const apiFetch = <T>(url: string, opts: Parameters<typeof $fetch>[1] = {}): Promise<T> => {
    const authHeaders = () => authStore.accessToken
      ? { Authorization: `Bearer ${authStore.accessToken}` }
      : {}

    return $fetch<T>(url, {
      baseURL: config.public.apiBase,
      ...opts,
      headers: { ...authHeaders(), ...(opts.headers as Record<string, string> ?? {}) },
    }).catch(async (e) => {
      if (e?.status !== 401) throw e

      const refreshed = await authStore.refresh()
      if (!refreshed) {
        await navigateTo('/login')
        throw e
      }

      // Reexecuta com o novo token
      return $fetch<T>(url, {
        baseURL: config.public.apiBase,
        ...opts,
        headers: { ...authHeaders(), ...(opts.headers as Record<string, string> ?? {}) },
      })
    })
  }

  return apiFetch
}
