const PRESET_COLORS = [
  { label: 'Laranja', hex: '#F97316' },
  { label: 'Azul', hex: '#3B82F6' },
  { label: 'Verde', hex: '#22C55E' },
  { label: 'Roxo', hex: '#A855F7' },
  { label: 'Rosa', hex: '#EC4899' },
  { label: 'Ciano', hex: '#06B6D4' },
  { label: 'Vermelho', hex: '#EF4444' },
  { label: 'Amarelo', hex: '#EAB308' },
]

function hexToRgbParts(hex: string): string {
  const clean = hex.replace('#', '')
  const r = parseInt(clean.slice(0, 2), 16)
  const g = parseInt(clean.slice(2, 4), 16)
  const b = parseInt(clean.slice(4, 6), 16)
  return `${r} ${g} ${b}`
}

export const useTheme = () => {
  const theme = useState<'dark' | 'light'>('theme', () => 'dark')
  const accentHex = useState<string>('accentHex', () => '#F97316')

  const applyTheme = () => {
    if (import.meta.server) return
    const html = document.documentElement
    if (theme.value === 'light') {
      html.classList.add('light')
    } else {
      html.classList.remove('light')
    }
    html.style.setProperty('--accent-rgb', hexToRgbParts(accentHex.value))
  }

  const setTheme = (t: 'dark' | 'light') => {
    theme.value = t
    localStorage.setItem('hub-theme', t)
    applyTheme()
  }

  const setAccent = (hex: string) => {
    accentHex.value = hex
    localStorage.setItem('hub-accent', hex)
    applyTheme()
  }

  const initTheme = () => {
    if (import.meta.server) return
    const savedTheme = localStorage.getItem('hub-theme') as 'dark' | 'light' | null
    const savedAccent = localStorage.getItem('hub-accent')
    theme.value = savedTheme || 'dark'
    accentHex.value = savedAccent || '#F97316'
    applyTheme()
  }

  return { theme, accentHex, presets: PRESET_COLORS, setTheme, setAccent, initTheme }
}
