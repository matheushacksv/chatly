# Projeto Hub - GEMINI.md

Este documento serve como guia de contexto e instruções para interações com a IA neste repositório. O Projeto Hub é uma plataforma multi-tenant de chatbot via WhatsApp com orquestração de agentes de IA, mensagens em tempo real e RAG (Retrieval-Augmented Generation).

## 🚀 Visão Geral do Projeto

- **Objetivo:** Plataforma para gestão de atendimentos via WhatsApp com suporte a agentes de IA (OpenAI, Anthropic, Groq).
- **Backend:** Django 6 + Django Ninja (API REST rápida e tipada).
- **Frontend:** Nuxt 3 + Vue 3 + Tailwind CSS.
- **Infraestrutura:** PostgreSQL 16, Redis (Broker/Cache), Celery (Tarefas Assíncronas), Django Channels (WebSockets).
- **Integrações:** EvoGO (WhatsApp API), Agno (Orquestração de IA), Groq (Transcrição de áudio).

---

## 🛠️ Comandos de Desenvolvimento

### Infraestrutura
A infraestrutura local (PostgreSQL + Redis) é gerenciada via Docker:
```bash
cd hub
docker-compose up -d
```

### Backend (`/hub`)
O backend utiliza `uv` para gerenciamento de dependências.
```bash
# Instalar dependências
uv pip install -e .

# Banco de Dados
python manage.py migrate

# Servidores
python manage.py runserver              # API e WebSockets (Daphne)
celery -A core worker -l info           # Worker para tarefas pesadas
celery -A core beat -l info             # Tarefas agendadas
```

### Frontend (`/hub-frontend`)
```bash
npm install
npm run dev      # Servidor de desenvolvimento na porta 3000
npm run build    # Build de produção
```

---

## 🏗️ Arquitetura e Convenções

### Multi-tenancy
- **Filtro Global:** Quase todos os modelos possuem uma chave estrangeira para `Organization`. 
- **Segurança:** Endpoints devem filtrar dados baseados no `request.auth.organization`.
- **Papéis:** `owner`, `admin`, `member` controlam o acesso via `PermissionGroup`.

### Padrões de Código (Backend)
- **Normalização de Telefone:** Use `core.utils.phone.normalize_phone()` para tratar números brasileiros (ajuste do 9º dígito).
- **Criptografia:** Chaves de API e segredos sensíveis usam `EncryptedTextField`. Requer `FIELD_ENCRYPTION_KEY`.
- **Django Ninja:** 
    - Rotas literais (ex: `/import`) devem vir **antes** de rotas parametrizadas (ex: `/{id}`).
    - Campos ManyToMany em Schemas exigem `resolve_` estáticos para serialização correta.
- **Async:** Transcrições, processamento de documentos e inferência de IA são sempre delegados ao Celery.

### Padrões de Código (Frontend)
- **Composables:** 
    - `useApi()`: Wrapper para fetch com refresh automático de token JWT.
    - `useOrgWs()`: Gerencia WebSockets para atualizações da inbox em tempo real.
- **Estado:** Pinia é usado para `auth` e `labels` (cache lazy).
- **Componentes:** Prefira componentes reutilizáveis em `components/` (ex: `LabelSelector`, `Chat`).

---

## 📂 Estrutura de Pastas

### Backend (`hub/`)
- `accounts/`: Usuários, organizações e convites.
- `agents/`: Configuração de agentes de IA e documentos (RAG).
- `contacts/`: CRM de contatos e importação CSV.
- `conversations/`: Mensagens, anexos e lógica de chat.
- `integrations/`: Conexão com instâncias WhatsApp (EvoGO).
- `labels/`: Etiquetas dinâmicas para contatos e conversas.
- `core/`: Configurações centrais, roteamento de API e utilitários.

### Frontend (`hub-frontend/`)
- `pages/`: Estrutura de rotas do Nuxt.
- `components/`: UI dividida por domínio (agents, contacts, conversations, etc).
- `stores/`: Estados globais via Pinia.
- `composables/`: Lógica compartilhada (API, WS, Paginação).

---

## 🧪 Testes
Testes Django estão localizados em arquivos `tests.py` dentro de cada app.
```bash
cd hub
python manage.py test
```

---

## ⚠️ Notas Importantes
- **Webhooks:** O `BASE_URL` no `.env` do backend deve ser uma URL pública (ex: ngrok) para que o WhatsApp consiga enviar eventos de volta para a plataforma.
- **EvoGO:** Certifique-se de que a `EVOGO_GLOBAL_API_KEY` está configurada para gerenciar as instâncias.
