// Singleton da conexão WS — persiste fora do ciclo de vida dos componentes
let _ws: WebSocket | null = null
let _reconnectTimeout: ReturnType<typeof setTimeout> | null = null
let _heartbeat: ReturnType<typeof setInterval> | null = null
let _onVisibility: (() => void) | null = null
// Backoff: nº de reconexões seguidas que NÃO estabilizaram.
let _reconnectAttempts = 0
// Timer que só dispara refetch/reset do backoff se a conexão sobreviver.
let _openSettleTimer: ReturnType<typeof setTimeout> | null = null

export const useOrgWs = () => {
  const authStore = useAuthStore()
  const config = useRuntimeConfig()
  const route = useRoute()
  const api = useApi()
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
  // Reconciliação confiável (equivalente ao F5, sem reload)
  // Re-busca a lista via REST e reidrata o estado. Usado no (re)connect do
  // socket e ao voltar o foco/visibilidade da aba — garante que a sidebar não
  // fique presa stale se o WS tiver morrido silenciosamente.
  // -------------------------------------------------------------------
  const refetch = async () => {
    if (!authStore.accessToken) return
    try {
      const data = await api<any[]>('/api/conversations/')
      initFromRest(data)
    } catch {}
  }

  const startHeartbeat = () => {
    if (_heartbeat) clearInterval(_heartbeat)
    // OrgConsumer.receive é no-op → ping mantém a conexão viva e detecta morte
    _heartbeat = setInterval(() => {
      if (_ws && _ws.readyState === WebSocket.OPEN) _ws.send(JSON.stringify({ type: 'ping' }))
    }, 25000)
  }

  const stopHeartbeat = () => {
    if (_heartbeat) { clearInterval(_heartbeat); _heartbeat = null }
  }

  const bindVisibility = () => {
    if (!process.client || _onVisibility) return
    _onVisibility = () => {
      if (document.visibilityState === 'visible') { connect(); refetch() }
    }
    document.addEventListener('visibilitychange', _onVisibility)
    window.addEventListener('focus', _onVisibility)
  }

  const unbindVisibility = () => {
    if (!process.client || !_onVisibility) return
    document.removeEventListener('visibilitychange', _onVisibility)
    window.removeEventListener('focus', _onVisibility)
    _onVisibility = null
  }

  // -------------------------------------------------------------------
  // Conexão WebSocket
  // -------------------------------------------------------------------
  const connect = () => {
    if (!process.client) return
    // Liga o self-heal por foco/visibilidade já aqui — assim funciona via REST
    // mesmo que o socket nunca chegue a abrir.
    bindVisibility()
    // Já conectado ou conectando
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) return
    if (!authStore.accessToken) {
      // Sem token agora (ex: refresh em andamento) — tenta de novo em breve
      // para a cadeia de reconexão não morrer em silêncio.
      _reconnectTimeout = setTimeout(() => connect(), 3000)
      return
    }

    const wsBase = config.public.apiBase.replace(/^http/, 'ws')
    _ws = new WebSocket(`${wsBase}/ws/org/?token=${authStore.accessToken}`)

    _ws.onopen = () => {
      startHeartbeat()
      // NÃO refetch no open imediato: se o server fecha 1011 logo após o accept,
      // o refetch a cada ciclo vira tempestade de GET. Só reconcilia e zera o
      // backoff se a conexão SOBREVIVER (>2s) — sinal de socket realmente saudável.
      if (_openSettleTimer) clearTimeout(_openSettleTimer)
      _openSettleTimer = setTimeout(() => {
        _reconnectAttempts = 0
        refetch()  // catch-up do que foi perdido enquanto o socket esteve morto
      }, 2000)
    }

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
      stopHeartbeat()
      if (_openSettleTimer) { clearTimeout(_openSettleTimer); _openSettleTimer = null }
      console.warn('[OrgWS] fechado', event.code)  // capturado pelo Sentry em prod
      if (event.code === 4001) {
        const refreshed = await authStore.refresh()
        if (refreshed) connect()
        else { navigateTo('/login'); return }
        return
      }
      if (event.code === 4003) return  // Sem acesso
      // Backoff exponencial + jitter: socket que cai/é recusado (ex: 1011 do server)
      // não martela a cada 3s. 3s,6s,12s,24s… cap 30s. Reset só em conexão estável.
      const delay = Math.min(30000, 3000 * 2 ** _reconnectAttempts) + Math.random() * 1000
      _reconnectAttempts++
      _reconnectTimeout = setTimeout(() => connect(), delay)
    }

    _ws.onerror = (e) => {
      console.warn('[OrgWS] erro de conexão', e)
      _ws?.close()
    }
  }

  const disconnect = () => {
    unbindVisibility()
    stopHeartbeat()
    if (_openSettleTimer) { clearTimeout(_openSettleTimer); _openSettleTimer = null }
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
