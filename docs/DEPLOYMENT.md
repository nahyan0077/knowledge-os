# Deployment Guide

Complete instructions for deploying Knowledge OS to production.

---

## Environment Variables

### Backend (`KNOWLEDGE_OS_*`)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...localhost` | Yes | PostgreSQL connection string |
| `JWT_SECRET` | — | Yes | Secret key for JWT signing (min 32 chars) |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Yes | Allowed CORS origins (JSON array) |
| `ACCESS_TOKEN_TTL_MINUTES` | `15` | No | Access token expiry |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | No | Refresh token expiry |
| `SECURE_COOKIES` | `false` | No | Set to `true` in production |
| `STORAGE_PROVIDER` | `local` | No | `local`, `supabase`, or `azure_blob` |
| `SUPABASE_URL` | — | If using Supabase | Supabase project URL |
| `SUPABASE_S3_ENDPOINT` | — | If using Supabase | Supabase S3-compatible endpoint |
| `SUPABASE_REGION` | — | If using Supabase | Supabase region |
| `SUPABASE_KEY` | — | If using Supabase | S3 access key ID |
| `SUPABASE_SECRET_KEY` | — | If using Supabase | S3 secret access key |
| `SUPABASE_STORAGE_BUCKET` | `documents` | No | Storage bucket name |
| `EMBEDDING_PROVIDER` | `openai` | No | `openai` or `gemini` |
| `OPENAI_API_KEY` | — | If using OpenAI | OpenAI API key |
| `GEMINI_API_KEY` | — | If using Gemini | Google Gemini API key |
| `QDRANT_URL` | `http://localhost:6333` | Yes | Qdrant instance URL |
| `QDRANT_API_KEY` | — | If using Qdrant Cloud | Qdrant API key |
| `TEMPORAL_HOST` | `localhost:7233` | If using Temporal | Temporal server address |
| `TEMPORAL_NAMESPACE` | `default` | If using Temporal | Temporal namespace |
| `TEMPORAL_API_KEY` | — | If using Temporal Cloud | Temporal Cloud API key |
| `PROCESSING_MODE` | `temporal` | No | `temporal` or `sync` |

### Frontend (`NEXT_PUBLIC_*`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (e.g. `https://knowledge-os-backend.onrender.com`) |

---

## Option 1: Render + Vercel

### Backend (Render)

1. Push to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your repo — Render reads `render.yaml` automatically
4. Set required env vars in the Render dashboard:
   - `KNOWLEDGE_OS_DATABASE_URL` — Use Render Postgres, Supabase DB, or Neon
   - `KNOWLEDGE_OS_JWT_SECRET` — Generate with `openssl rand -hex 32`
   - `KNOWLEDGE_OS_CORS_ORIGINS` — `["https://your-app.vercel.app"]`
   - `KNOWLEDGE_OS_STORAGE_PROVIDER` — `supabase`
   - `KNOWLEDGE_OS_SUPABASE_KEY` / `SECRET_KEY` — From Supabase Storage Settings → Access keys
   - `KNOWLEDGE_OS_GEMINI_API_KEY` — From Google AI Studio
   - `KNOWLEDGE_OS_QDRANT_URL` — From Qdrant Cloud dashboard
   - `KNOWLEDGE_OS_QDRANT_API_KEY` — From Qdrant Cloud API keys
5. Deploy — Render builds the Docker image and runs migrations automatically

### Frontend (Vercel)

```bash
cd frontend
npx vercel --prod
```

Set `NEXT_PUBLIC_API_URL` to your Render backend URL in Vercel dashboard.

---

## Option 2: Docker Compose

```bash
docker compose up -d --build
```

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | `http://localhost:8000/docs` |
| Qdrant | 6333 | `http://localhost:6333/dashboard` |
| Temporal | 7233 | — |
| Temporal UI | 8080 | `http://localhost:8080` |

---

## Processing Modes

Knowledge OS supports two document processing modes controlled by `KNOWLEDGE_OS_PROCESSING_MODE`:

| Mode | Behavior | When to Use |
|------|----------|-------------|
| `temporal` (default) | Async processing via Temporal workflow engine | During 90-day Temporal free trial |
| `sync` | Inline processing — no Temporal needed | After trial expires / to save costs |

### Temporal Mode

Requires Temporal server (self-hosted or Temporal Cloud) and a separate worker process.

**Temporal Cloud** (managed):
- Sign up at [temporal.io](https://temporal.io) — $1,000 free credits for 90 days
- After trial: $100/month (Essentials plan)

**Self-hosted Temporal** (free):
- Included in `docker-compose.yml`
- For production, run on a VPS with Docker

### Sync Mode

No external dependencies. Documents process inline during upload (5-30 seconds).

To switch:
1. Set `KNOWLEDGE_OS_PROCESSING_MODE=sync` on your hosting platform
2. Remove the worker service (if any)
3. Redeploy

---

## Infrastructure Setup

### Supabase Storage

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Storage** → **Settings** → **Access keys**
3. Create a new S3 access key
4. Copy the access key ID and secret key

### Qdrant Cloud

1. Create an account at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a free cluster (N. Virginia recommended)
3. Copy the cluster URL and create an API key

### Gemini API

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
