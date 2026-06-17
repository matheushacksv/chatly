# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão Geral

Plataforma multi-tenant de chatbot via WhatsApp com orquestração de agentes de IA (OpenAI/Anthropic/Groq), mensagens em tempo real e RAG com documentos.

**Stack:** Django 6 + Django Ninja (backend) | Nuxt 3 + Vue 3 (frontend) | PostgreSQL 16 | Redis | Celery | Django Channels | Agno (IA)

## Comandos

### Backend (`/hub`)

```bash
# Infraestrutura local (PostgreSQL + Redis)
docker-compose up -d

# Instalar dependências
uv pip install -e .

# Migrations
python manage.py makemigrations
python manage.py migrate

# Servidor de desenvolvimento
python manage.py runserver

# Worker Celery (terminal separado)
celery -A core worker -l info

# Celery Beat — tarefas agendadas
celery -A core beat -l info
```

### Frontend (`/hub-frontend`)

```bash
npm install
npm run dev      # dev server na porta 3000
npm run build
npm run preview
```

## Arquitetura

### Multi-tenancy
Todos os models possuem `organization` FK. Endpoints filtram por `request.auth.organization` (usuário autenticado via JWT). Permissões: roles `owner/admin/member` + `PermissionGroup` para controle granular.

### Fluxo de dados
```
Frontend (useApi.ts + Pinia) → /api/* (Django Ninja) → PostgreSQL
                                     ↓
                              Celery (Redis broker) → Agno (IA)
                                     ↓
                              EvoGO (WhatsApp API)
```

### Routers da API (`hub/core/api.py`)
| Prefix | Módulo |
|--------|--------|
| `/api/auth/` | accounts — register, login, refresh, me |
| `/api/org/` | accounts — org, membros, convites (listar/revogar/reenviar pendentes) |
| `/api/agents/` | agents — CRUD + documentos + providers |
| `/api/conversations/` | conversations — mensagens, anexos |
| `/api/contacts/` | contacts — CRUD, anotações, importação CSV, etiquetas |
| `/api/templates/` | templates de mensagem |
| `/api/automations/` | automations — CRUD, triggers/actions meta, runs |
| `/api/integrations/whatsapp/` | instâncias WhatsApp |
| `/api/webhooks/whatsapp/` | webhook incoming (sem auth) |
| `/api/labels/` | labels — CRUD de etiquetas da org |
| `/api/public/` | API pública por org (auth via `Bearer` api_key) — criar contato + iniciar automação |

**WebSockets:**
- `ws://.../api/ws/org/` — atualizações de nível org (lista de conversas)
- `ws://.../api/ws/conversations/<id>/` — chat em tempo real

> **Realtime do chat — fallback via Org WS:** o socket por-conversa (`Chat.vue:connectWs`) é frágil (vive só enquanto o componente está montado); o Org WS (`useOrgWs`, singleton conectado no layout) é confiável. Para garantir que a área de chat atualize mesmo se o socket por-conversa falhar, `Chat.vue` observa `last_message.id` da conversa no store reativo do `useOrgWs` e, ao detectar id novo ausente, chama `syncNewMessages()` → `GET /messages?after_id=<maxLocalId>` (param dedicado, `id__gt` ascendente; `before_id` = paginação p/ trás). Dedup por id evita duplicar quando os dois caminhos entregam. Backend de push (`notify_new_message` vs `notify_conversation_list_updated`) é simétrico/Redis; o gargalo era sempre client-side. Regressão em `conversations/test_messages_after_id.py`.

> **Realtime da sidebar — self-heal do Org WS:** a lista lateral depende SÓ do Org WS (`useOrgWs`), sem fonte p/ piggyback. Para não ficar stale quando o socket morre (ex: restart de deploy), `useOrgWs` tem: `refetch()` (`GET /api/conversations/` → `initFromRest`) disparado no `onopen` (catch-up) e nos eventos `visibilitychange`/`focus` da aba (F5 sem reload, ligado já no `connect()` p/ funcionar via REST mesmo se o WS nunca abrir); heartbeat ping ~25s (`OrgConsumer.receive` é no-op); reconexão que reagenda mesmo sem token momentâneo; `console.warn('[OrgWS]'...)` p/ Sentry. **Regra de produto:** a sidebar reordena SÓ para mensagem **inbound** (`webhook.py` empurra `notify_conversation_list_updated`); respostas de IA (`tasks.py`) NÃO empurram a lista de propósito — evita cascata de reordenação com N agentes ativos. NÃO adicionar push de IA na sidebar.

### Processamento assíncrono (Celery)
- Transcrição de áudio via Groq
- Processamento de documentos (PDF → embedding no system prompt)
- Inferência do agente via Agno
- Envio de mensagens agendadas

Ver `conversations/tasks.py` e `agents/tasks.py`.

### Padrões não óbvios
- **Telefone:** `core.utils.phone.normalize_phone()` insere o 9 após o DDD brasileiro para compatibilidade WhatsApp.
- **API keys criptografadas:** `EncryptedTextField` via `django-encrypted-model-fields`; requer `FIELD_ENCRYPTION_KEY` no `.env`.
- **Status de documento:** `pending → processing → ready | failed` (atualizado por Celery).
- **Roles de mensagem:** `user`, `assistant`, `system`, `operator` (intervenção manual).
- **Convites pendentes:** `Invite.accepted` (bool) = pendente quando `False`; `is_valid()` exige não-aceito E `expires_at > now`. Gestão (owner/admin) em `accounts/org_api.py`: `GET /api/org/invites` (lista `accepted=False`, schema `InviteOut` calcula `is_expired`), `DELETE /api/org/invites/{id}` (**hard delete** → `accept_invite` faz `get_object_or_404(Invite, token=...)`, então token revogado dá 404), `POST /api/org/invites/{id}/resend` (renova `expires_at` +7d, **mesmo token**, redispara `send_invite_email.delay`). `create_invite` bloqueia 2º convite p/ email com `accepted=False` existente — por isso revogar destrava reenvio manual. Frontend: seção "Convites pendentes" na aba Membros de `/org` (badge "Expirado", reenviar, revogar). Regressão em `accounts/tests.py`.
- **Agno:** camada de abstração sobre OpenAI/Anthropic/Groq — troca de provider sem mudar lógica de negócio.
- **Frontend — token refresh:** `useApi.ts` intercepta 401 e tenta renovar o access token automaticamente; store Pinia sincroniza com `localStorage`.
- **Django Ninja — ordenação de rotas:** rotas literais (ex: `/import`, `/labels`) DEVEM ser definidas ANTES das rotas parametrizadas (`/{id}`) no mesmo router; caso contrário o parâmetro captura o literal e retorna 405.
- **Django Ninja — M2M fields:** campos ManyToMany em schemas precisam de `resolve_*` estático (`@staticmethod def resolve_labels(obj): return obj.labels.all()`); sem ele o manager é serializado como lista vazia silenciosamente.
- **Importação CSV:** endpoint `POST /api/contacts/import` aceita multipart com campo `file`; colunas `name` e `phone` obrigatórias, `email` opcional, demais colunas viram `custom_fields`.
- **Automations — ações:** registry `ACTION_HANDLERS` + `@register('nome')` em `automations/actions.py`; `execute_action(step, run_context, organization_id)` despacha por `step.action_type`. Metadados de UI em `ACTIONS_META`/`TRIGGERS_META` (`api.py`).
- **Automations — PATCH recria steps:** `automation.steps.all().delete()` + `_save_steps` (DFS, reatribui `order`). Estado que precisa sobreviver à edição NÃO pode viver no `AutomationStep` — vai no model `Automation`.
- **Automations — variações de mensagem:** `send_message` aceita `config.variants = [{text, weight}]`; rodízio determinístico por peso (gcd-reduzido) via `automations/variants.py`. Contador persistido em `Automation.variant_state` (JSONField keyed por `step.order`), sobrevive ao PATCH. `variants` vazio → usa `config.text`.
- **Automations — encadeamento:** ação `start_automation` dispara outra automação; só mira alvos com `trigger_type='automation.chained'` (gatilho "Iniciada por automação", nunca disparado por evento). Guarda anti-loop via `_auto_depth` no contexto (cap `MAX_AUTO_DEPTH=5`).
- **Agente por conversa (override):** `Conversation.agent` é FK independente do `instance.agent` (oficial). Webhook só usa `instance.agent` quando `conversation.agent` é null (`integrations/webhook.py`); `process_message` roda `conversation.agent`. Trocar o agente de uma conversa NÃO afeta as demais. Override é permanente até nova troca. Mecanismos: ação de automação `switch_agent` (`config.agent_id` + `config.ai_state` ∈ `on|off|keep` controla `ai_active` de forma explícita; compat: `activate` bool antigo → `on`/`keep`) e PATCH manual `PATCH /api/conversations/{id}` com `agent_id` (valor `0` limpa o override → volta ao oficial). Frontend: campo `agent_select` no StepEditor e dropdown no `Chat.vue` ("Agente oficial" = limpa override).
- **API pública por org:** `Organization.api_key` (CharField único, plaintext+`db_index` — auth busca por valor exato, como `PipedriveIntegration.webhook_secret`; criptografar impediria o lookup). Gerada via `Organization.generate_api_key()` (`secrets.token_urlsafe(32)`). Auth: `core.api_key_auth.ApiKeyAuth` (HttpBearer) — `request.auth` no router público é a **Organization**, NÃO um User. Endpoint `POST /api/public/contacts` (`contacts/public_api.py`): **upsert** por telefone normalizado (`normalize_phone`) — existente é atualizado (merge de `custom_fields`), não duplica; `contact.created` só dispara em criação nova (idempotente p/ retries). Disparo de automação tem 2 caminhos: (1) **idiomático** — gatilho `api.request` ("Requisição recebida (API)", em `TRIGGER_CHOICES`, só disparado por este endpoint como `automation.chained`) dispara em TODA chamada via `trigger_event('api.request', org.id, contact_id=.., source=data.source)`; org cria automação com esse gatilho e roteia por `trigger_filters={'source': x}` (sem precisar de id; editor mostra campo `source` só p/ esse trigger, sanitizado p/ não salvar vazio). (2) **override** — `automation_id` opcional roda uma automação específica ativa via `AutomationRun`+`run_automation.delay` (validada ANTES de mexer no contato → id inválido = 400 sem criar contato). Gestão da key: `GET /api/org/api-key` (lazy-generate) + `POST /api/org/api-key/regenerate` (owner/admin). Frontend: card "API pública" na aba Organização de `/settings`. Regressão em `contacts/test_public_api.py`.
- **Resolução de instância de envio:** SEMPRE via `conversations.tasks._resolve_instance(conversation)` (FK `conversation.instance` → `agent.whatsapp_instance` do oficial → qualquer instância CONNECTED da org). NUNCA resolver envio só por `agent.whatsapp_instance`: é OneToOne (`WhatsAppInstance.agent`, related_name `whatsapp_instance`) e só existe no agente OFICIAL — agente override levanta `RelatedObjectDoesNotExist`, então a IA gera resposta mas não envia. Todos os paths de envio usam o helper: `process_message`, `transcribe_and_process_message` (áudio), `send_follow_up`, `send_scheduled_message`. Envio manual do operador: `conversations/api.py:_get_instance` (mesma ordem, com try/except no acesso ao reverse). `Conversation.instance` é setado pelo webhook na criação e backfilled em inbounds antigos. Regressão coberta em `conversations/test_agent_override_send.py`.
- **WhatsApp — `LoggedIn` é a verdade, NÃO `Connected`:** o EvoGO `/instance/status` devolve `{Connected, LoggedIn}`. `Connected` é só o socket do gateway; `LoggedIn` é a sessão autenticada/usável. Confundir os dois fazia o app marcar CONNECTED com `Connected:true, LoggedIn:false` (sessão fantasma) → todo envio sumia silencioso. Fonte de verdade central em `integrations/services.classify_status(data) -> (status, needs_qr)`: `LoggedIn:true`→`('connected', False)`; `Connected:true, LoggedIn:false`→`('disconnected', True)` (logout/fantasma, **needs_qr** — `/connect` NÃO resolve, exige re-scan do QR); `Connected:false`→`('disconnected', False)` (socket caiu, recuperável via `/connect`). **Reconexão é event-driven (escala), não polling em massa:** webhook `Disconnected`→marca down + `reconnect_instance.delay`; webhook `LoggedOut`→`needs_qr=True`; **proof-of-life** no inbound (`webhook.py` recebeu msg = logado → reseta status/needs_qr/attempts + `last_seen_at`); falha no envio (`send_whatsapp_message`)→`reconnect_instance.delay`. Beat `sweep-instances` (3min, `integrations/tasks.py`) é só rede de segurança: fan-out `reconnect_instance.delay` SÓ no conjunto caído (`exclude(needs_qr=True).filter(status in [disconnected, connecting])`), nunca em todas. `reconnect_instance` curto-circuita se `needs_qr` (não martela o EvoGO); após `MAX_RECONNECT_ATTEMPTS=5` connects sem logar → `needs_qr=True`. **Flap fix:** webhook `Connected`/`PairSuccess` NÃO chama `connect_instance` de novo (o antigo `_register_webhook` reconectava por cima a cada evento → loop connect→Connected→connect, sessão nunca estabilizava). Campos no model: `needs_qr`, `reconnect_attempts`, `last_seen_at`. Frontend: badge "Escanear QR" em `/instances` quando `needs_qr`. Regressão em `integrations/test_instance_reconnect.py`.
- **WS / channel layer — NÃO bumpar redis-py p/ 7.x:** `redis` está pinado `>=5.0.1,<6` (`hub/pyproject.toml`) de propósito. redis-py 7.x aplica socket read timeout no comando bloqueante do `channels-redis` (`channel_receive`, read da fila do canal, ~`expiry`=60s) **sem margem** → ao fim do expiry estoura `redis.exceptions.TimeoutError: Timeout reading from redis` em vez de retornar vazio → consumer morre → Daphne fecha o WS com **1011**. Em prod isso virava loop de reconexão + tempestade de requests sobre o Daphne único (HTTP+WS no mesmo processo) → app inteira lenta e até SSH sufocado. Mantido `RedisChannelLayer` (NÃO trocar p/ `RedisPubSubChannelLayer`: quebraria o `group_send` via `async_to_sync` vindo do worker Celery). Defesas client/server complementares: `OrgConsumer/ChatConsumer.connect` guardam `group_add` com `logger.exception` + close(1011) explícito; `useOrgWs.ts` usa backoff exponencial+jitter no reconnect e gate de 2s no `refetch` (não martela GET se o socket morre logo após abrir).

## Apps Django

| App | Responsabilidade |
|-----|-----------------|
| `accounts` | User, Organization, PermissionGroup, convites |
| `agents` | AIAgent, documentos, providers (OpenAI/Anthropic/Groq) |
| `contacts` | Contact, ContactAnnotation — CRM |
| `conversations` | Conversation, Message, MessageAttachment, Sticker |
| `labels` | Label — etiquetas aplicáveis a Contact e Conversation via M2M |
| `templates` | MessageTemplate |
| `automations` | Automation, AutomationStep (árvore if/else), AutomationRun — motor de gatilho→ações |
| `integrations` | WhatsAppInstance + webhook EvoGO |
| `core` | settings, api.py (NinjaAPI), utils (phone, errors) |

## Frontend — Estrutura

### Stores Pinia (`hub-frontend/stores/`)
| Store | Responsabilidade |
|-------|-----------------|
| `auth.ts` | tokens JWT, user, login/logout/refresh |
| `labels.ts` | cache de etiquetas da org; fetch lazy (uma vez por sessão) |

### Páginas principais
| Rota | Arquivo | Descrição |
|------|---------|-----------|
| `/conversations` | `pages/conversations/index.vue` | Inbox com chat em tempo real |
| `/contacts` | `pages/contacts/index.vue` | CRM — lista + detalhe + anotações + etiquetas |
| `/labels` | `pages/labels/index.vue` | CRUD de etiquetas da organização |
| `/agents` | `pages/agents/` | Gestão de agentes de IA |
| `/templates` | `pages/templates/` | Templates de mensagem |
| `/instances` | `pages/instances/` | Instâncias WhatsApp (owner/admin) |
| `/org` | `pages/org/index.vue` | Membros e grupos de permissão |
| `/settings` | `pages/settings/` | Configurações do usuário |

### Componentes notáveis
| Componente | Função |
|-----------|--------|
| `components/conversations/Chat.vue` | Chat completo — mensagens, mídia, áudio, stickers, agendamento, etiquetas, anotações |
| `components/conversations/AnnotationPanel.vue` | Painel flutuante de anotações do contato |
| `components/contacts/ImportModal.vue` | Modal de importação CSV com drag&drop |
| `components/labels/LabelBadge.vue` | Pill colorida de etiqueta (read-only) |
| `components/labels/LabelSelector.vue` | Dropdown interativo para atribuir etiquetas a contact ou conversation |
| `components/AppSidebar.vue` | Sidebar responsiva com collapse |

### Padrões de frontend
- **useApi():** composable wrapper sobre `$fetch` com auth header e retry de 401 automático.
- **useConfirm():** modal de confirmação reutilizável — `await confirm('mensagem', { title })`.
- **usePagination():** paginação client-side — `{ page, totalPages, paged, prev, next }`.
- **useOrgWs():** WebSocket da org — mantém lista de conversas em tempo real; inicializado via `initFromRest()`.
- **Etiquetas:** `useLabelsStore()` faz fetch lazy; `LabelSelector` lida com atribuição via `POST /api/{contacts|conversations}/{id}/labels` com `{ label_ids: [...] }` (substitui o set completo).

## Variáveis de Ambiente (`hub/.env`)

```
SECRET_KEY=
DEBUG=True
POSTGRES_DB=hub
POSTGRES_USER=hub_user
POSTGRES_PASSWORD=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_URL=redis://localhost:6380/0
MINIO_ENDPOINT_URL=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET_NAME=hub
GROQ_API_KEY=
EVOGO_BASE_URL=
EVOGO_GLOBAL_API_KEY=
BASE_URL=                    # URL pública para webhooks (ex: ngrok)
FIELD_ENCRYPTION_KEY=        # base64 — obrigatório para campos criptografados
FRONTEND_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000
```
