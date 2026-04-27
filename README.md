# ChatlyAi

Plataforma multi-tenant de atendimento via WhatsApp com orquestração de agentes de IA.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Django 6 + Django Ninja + Daphne (ASGI) |
| Frontend | Nuxt 3 + Vue 3 + Tailwind CSS |
| Banco | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Fila | Celery + Celery Beat |
| IA | Agno (OpenAI / Anthropic / Groq) |
| WhatsApp | EvoGO |
| Storage | MinIO (S3-compatible) |

## Estrutura

```
projeto-hub/
├── hub/              # Backend Django
└── hub-frontend/     # Frontend Nuxt 3
```

## Desenvolvimento local

### Pré-requisitos

- Python 3.13+ com `uv`
- Node.js 20+
- Docker (para PostgreSQL e Redis)

### Backend

```bash
cd hub
docker-compose up -d          # sobe PostgreSQL + Redis
cp .env.example .env          # preencher variáveis
uv pip install -e .
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Em terminais separados:

```bash
celery -A core worker -l info
celery -A core beat -l info
```

### Frontend

```bash
cd hub-frontend
cp .env.example .env          # ajustar NUXT_PUBLIC_API_BASE se necessário
npm install
npm run dev                   # http://localhost:3000
```

## Deploy (VPS + Docker)

Ver `hub/docker-compose.prod.yml` e `nginx/chatlyai.conf`.

Passos resumidos:

```bash
# Backend
cd hub && cp .env.example .env   # preencher valores de produção
docker compose -f docker-compose.prod.yml up -d
docker compose exec web python manage.py migrate

# Frontend
cd hub-frontend && npm run generate
cp -r .output/public/* /var/www/chatlyai/
```
