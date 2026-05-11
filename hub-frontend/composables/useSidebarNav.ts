export const allNavItems = [
  { label: 'Dashboard',     icon: 'solar:widget-2-bold-duotone',           to: '/' },
  { label: 'Conversas',     icon: 'solar:chat-round-line-duotone',          to: '/conversations' },
  { label: 'Contatos',      icon: 'solar:users-group-rounded-bold-duotone', to: '/contacts' },
  { label: 'Agentes',       icon: 'solar:cpu-bolt-bold-duotone',            to: '/agents',    requireAgentPermission: true },
  { label: 'Campanhas',     icon: 'solar:screencast-outline',                 to: '/campaigns' },
  { label: 'Templates',     icon: 'solar:document-text-bold-duotone',       to: '/templates' },
  { label: 'Etiquetas',     icon: 'solar:tag-bold-duotone',                 to: '/labels' },
  { label: 'Automações',    icon: 'solar:bolt-circle-bold-duotone',         to: '/automations' },
  { label: 'Instâncias',    icon: 'solar:smartphone-2-bold-duotone',        to: '/instances', ownerAdminOnly: true },
  { label: 'Organização',   icon: 'solar:buildings-2-bold-duotone',         to: '/org',       ownerAdminOnly: true },
  { label: 'Plano',       icon: 'solar:card-bold-duotone',                to: '/billing',   ownerAdminOnly: true },
  { label: 'Configurações', icon: 'solar:settings-bold-duotone',            to: '/settings' },
] as const

const HIDDEN_KEY = 'hub-sidebar-hidden'
const ORDER_KEY  = 'hub-sidebar-order'

export const useSidebarNav = () => {
  const hiddenPaths = useState<string[]>('sidebar-hidden', () => {
    if (process.client) {
      const saved = localStorage.getItem(HIDDEN_KEY)
      if (saved) { try { return JSON.parse(saved) } catch {} }
    }
    return []
  })

  const navOrder = useState<string[]>('sidebar-order', () => {
    if (process.client) {
      const saved = localStorage.getItem(ORDER_KEY)
      if (saved) { try { return JSON.parse(saved) } catch {} }
    }
    return allNavItems.map(i => i.to)
  })

  const setHidden = (paths: string[]) => {
    hiddenPaths.value = paths
    if (process.client) {
      if (paths.length === 0) localStorage.removeItem(HIDDEN_KEY)
      else localStorage.setItem(HIDDEN_KEY, JSON.stringify(paths))
    }
  }

  const setOrder = (paths: string[]) => {
    navOrder.value = paths
    if (process.client) localStorage.setItem(ORDER_KEY, JSON.stringify(paths))
  }

  const orderedAllItems = computed(() => {
    const order = navOrder.value
    return [...allNavItems].sort((a, b) => {
      const ai = order.indexOf(a.to)
      const bi = order.indexOf(b.to)
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
    })
  })

  return { hiddenPaths, setHidden, navOrder, setOrder, orderedAllItems }
}
