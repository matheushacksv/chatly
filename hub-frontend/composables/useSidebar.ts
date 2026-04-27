export const useSidebar = () => {
  const isOpen = useState('sidebar-open', () => false)
  const open = () => { isOpen.value = true }
  const close = () => { isOpen.value = false }
  const toggle = () => { isOpen.value = !isOpen.value }

  const isCollapsed = useState('sidebar-collapsed', () => {
    if (import.meta.client) {
      return localStorage.getItem('sidebar-collapsed') === 'true'
    }
    return false
  })

  const toggleCollapsed = () => {
    isCollapsed.value = !isCollapsed.value
    if (import.meta.client) {
      localStorage.setItem('sidebar-collapsed', String(isCollapsed.value))
    }
  }

  return { isOpen, open, close, toggle, isCollapsed, toggleCollapsed }
}
