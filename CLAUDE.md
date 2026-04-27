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
| `/api/org/` | accounts — org, membros, convites |
| `/api/agents/` | agents — CRUD + documentos + providers |
| `/api/conversations/` | conversations — mensagens, anexos |
| `/api/contacts/` | contacts — CRUD, anotações, importação CSV, etiquetas |
| `/api/templates/` | templates de mensagem |
| `/api/integrations/whatsapp/` | instâncias WhatsApp |
| `/api/webhooks/whatsapp/` | webhook incoming (sem auth) |
| `/api/labels/` | labels — CRUD de etiquetas da org |

**WebSockets:**
- `ws://.../api/ws/org/` — atualizações de nível org (lista de conversas)
- `ws://.../api/ws/conversations/<id>/` — chat em tempo real

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
- **Agno:** camada de abstração sobre OpenAI/Anthropic/Groq — troca de provider sem mudar lógica de negócio.
- **Frontend — token refresh:** `useApi.ts` intercepta 401 e tenta renovar o access token automaticamente; store Pinia sincroniza com `localStorage`.
- **Django Ninja — ordenação de rotas:** rotas literais (ex: `/import`, `/labels`) DEVEM ser definidas ANTES das rotas parametrizadas (`/{id}`) no mesmo router; caso contrário o parâmetro captura o literal e retorna 405.
- **Django Ninja — M2M fields:** campos ManyToMany em schemas precisam de `resolve_*` estático (`@staticmethod def resolve_labels(obj): return obj.labels.all()`); sem ele o manager é serializado como lista vazia silenciosamente.
- **Importação CSV:** endpoint `POST /api/contacts/import` aceita multipart com campo `file`; colunas `name` e `phone` obrigatórias, `email` opcional, demais colunas viram `custom_fields`.

## Apps Django

| App | Responsabilidade |
|-----|-----------------|
| `accounts` | User, Organization, PermissionGroup, convites |
| `agents` | AIAgent, documentos, providers (OpenAI/Anthropic/Groq) |
| `contacts` | Contact, ContactAnnotation — CRM |
| `conversations` | Conversation, Message, MessageAttachment, Sticker |
| `labels` | Label — etiquetas aplicáveis a Contact e Conversation via M2M |
| `templates` | MessageTemplate |
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
