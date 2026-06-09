// Singleton da conexão WS — persiste fora do ciclo de vida dos componentes
let _ws: WebSocket | null = null
let _reconnectTimeout: ReturnType<typeof setTimeout> | null = null

export const useOrgWs = () => {
  const authStore = useAuthStore()
  const config = useRuntimeConfig()
  const route = useRoute()
  const { add: addUnread, remove: removeUnread } = useUnread()
  const { send: sendNotification } = useNotifications()

  // Estado global de conversas — compartilhado entre layout e página de conversas
  const conversations = useState<any[]>('org-conversations', () => [])
  // Último ID de mensagem visto por conversa
  const lastSeenMsgId = useState<Record<number, number>>('last-seen-msg-id', () => ({}))

  // Ordena por data da última mensagem (desc) — comportamento WhatsApp.
  // Fallback: started_at / created_at. Timestamps ISO comparam lexicograficamente.
  const sortKey = (c: any) => c.last_message?.created_at || c.started_at || c.created_at || ''
  const sortConversations = () => {
    conversations.value.sort((a, b) => {
      const ka = sortKey(a), kb = sortKey(b)
      return ka < kb ? 1 : ka > kb ? -1 : 0
    })
  }

  // -------------------------------------------------------------------
  // Lógica de notificação / unread
  // -------------------------------------------------------------------
  const handleIncoming = (conv: any) => {
    const msg = conv.last_message
    if (!msg || msg.role !== 'user') return

    const lastSeen = lastSeenMsgId.value[conv.id]
    if (lastSeen && msg.id <= lastSeen) return

    addUnread(conv.id)
    lastSeenMsgId.value[conv.id] = msg.id

    if (!process.client) return
    // Notifica se tab em background OU usuário está em outra rota
    const tabHidden = document.visibilityState !== 'visible'
    const otherRoute = route.path !== '/conversations'
    if (tabHidden || otherRoute) {
      sendNotification(conv.contact?.name || 'Nova mensagem', msg.content || '📎 Arquivo')
    }
  }

  // -------------------------------------------------------------------
  // Conexão WebSocket
  // -------------------------------------------------------------------
  const connect = () => {
    if (!process.client) return
    // Já conectado ou conectando
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) return
    if (!authStore.accessToken) return

    const wsBase = config.public.apiBase.replace(/^http/, 'ws')
    _ws = new WebSocket(`${wsBase}/ws/org/?token=${authStore.accessToken}`)

    _ws.onmessage = (event) => {
      const payload = JSON.parse(event.data)

      if (payload.type === 'new_conversation') {
        const conv = payload.conversation
        if (!conversations.value.some(c => c.id === conv.id)) {
          conversations.value.unshift(conv)
        }
        sortConversations()
        handleIncoming(conv)

      } else if (payload.type === 'conversation_list_updated') {
        const conv = payload.conversation
        const idx = conversations.value.findIndex(c => c.id === conv.id)
        if (idx !== -1) {
          conversations.value[idx] = { ...conversations.value[idx], ...conv }
        } else {
          conversations.value.unshift(conv)
        }
        sortConversations()
        handleIncoming(conv)
      }
    }

    _ws.onclose = async (event) => {
      if (event.code === 4001) {
        const refreshed = await authStore.refresh()
        if (refreshed) connect()
        else navigateTo('/login')
        return
      }
      if (event.code === 4003) return
      _reconnectTimeout = setTimeout(() => connect(), 3000)
    }

    _ws.onerror = () => _ws?.close()
  }

  const disconnect = () => {
    if (_reconnectTimeout) clearTimeout(_reconnectTimeout)
    if (_ws) { _ws.onclose = null; _ws.close(); _ws = null }
  }

  // -------------------------------------------------------------------
  // Chamado pela página de conversas ao carregar a lista via REST
  // Inicializa o lastSeenMsgId para não disparar notificações retroativas
  // -------------------------------------------------------------------
  const initFromRest = (convs: any[]) => {
    conversations.value = convs
    sortConversations()
    for (const conv of convs) {
      if (conv.last_message?.id) {
        lastSeenMsgId.value[conv.id] = conv.last_message.id
      }
    }
  }

  // Chamado quando o usuário abre uma conversa
  const markAsRead = (convId: number) => {
    removeUnread(convId)
    const conv = conversations.value.find(c => c.id === convId)
    if (conv?.last_message?.id) {
      lastSeenMsgId.value[convId] = conv.last_message.id
    }
  }

  return { connect, disconnect, conversations, initFromRest, markAsRead }
}
