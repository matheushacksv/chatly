type Consent = 'accepted' | 'rejected' | null

const STORAGE_KEY = 'cookie_consent'

// Estado compartilhado entre todos os componentes que usam o composable
const consent = ref<Consent>(null)
let loaded = false

export function useCookieConsent() {
  // Carrega a escolha do localStorage uma vez (apenas no cliente)
  if (!loaded && import.meta.client) {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'accepted' || stored === 'rejected') {
      consent.value = stored
    }
    loaded = true
  }

  const hasDecided = computed(() => consent.value !== null)

  function set(value: Exclude<Consent, null>) {
    consent.value = value
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, value)
    }
  }

  const accept = () => set('accepted')
  const reject = () => set('rejected')

  return { consent, hasDecided, accept, reject }
}
