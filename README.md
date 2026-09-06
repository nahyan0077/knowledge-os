<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/python-3.13-blue.svg" alt="Python 3.13">
  <img src="https://img.shields.io/badge/next.js-16-black.svg" alt="Next.js 16">
  <img src="https://img.shields.io/badge/status-active-brightgreen.svg" alt="Status">
</p>

<h1 align="center">Knowledge OS</h1>

<p align="center">
  <strong>AI-first, project-centric knowledge platform for documents, conversations,<br>retrieval, and durable workflows.</strong>
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#getting-started">Getting Started</a> ·
  <a href="#development">Development</a> ·
  <a href="docs/DEPLOYMENT.md">Deployment</a> ·
  <a href="#license">License</a>
</p>

---

## Overview

Knowledge OS is a full-stack RAG (Retrieval-Augmented Generation) platform that lets you upload documents, automatically process and index them, and chat with an AI that grounds its responses in your actual content — complete with source citations.

Built with Clean Architecture principles, multi-tenancy from day one, and a modular monolith backend designed for future decomposition.

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-tenant Auth** | JWT + Argon2 password hashing, refresh token rotation, Google OAuth |
| **Project Workspaces** | Organize documents and conversations per project with role-based access |
| **Document Management** | Upload, version, delete documents with automatic status tracking |
| **Document Processing** | Extract text → chunk → embed → index pipeline |
| **RAG Chat** | AI responses grounded in your documents with inline source citations |
| **PDF Viewer** | In-app PDF viewer with citation overlay |
| **Message Feedback** | Thumbs up/down on assistant responses for quality tracking |
| **Dashboard** | Project list with document and conversation stats |
| **Dual Processing** | Switch between Temporal workflow (async) and synchronous mode via env var |

---

## Architecture

```mermaid
graph TB
    User([User]) --> Frontend[Next.js Frontend]
    Frontend --> API[FastAPI Backend]
    API --> PostgreSQL[(PostgreSQL)]
    API --> Qdrant[(Qdrant)]
    API --> Storage[Supabase Storage]
    API --> LLM[LLM Providers<br/>OpenAI / Gemini / Anthropic]
    API --> Temporal[Temporal Server]
    Temporal --> Worker[Processing Worker]
    Worker --> Storage
    Worker --> Qdrant
    Worker --> PostgreSQL
```

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4, Zustand, TanStack Query |
| **Backend** | FastAPI, Python 3.13, SQLAlchemy Async, Alembic |
| **Database** | PostgreSQL (system of record) |
| **Vector Store** | Qdrant (derived, rebuildable) |
| **Object Storage** | Supabase Storage (S3-compatible) |
| **Workflows** | Temporal (or synchronous fallback) |
| **AI / Embeddings** | OpenAI, Google Gemini, Anthropic |
| **Auth** | JWT + Argon2, Google OAuth |
| **Deployment** | Render (backend), Vercel (frontend), Docker Compose (local) |

---

## Project Structure

```
├── backend/                  FastAPI modular monolith
│   ├── src/knowledge_os/
│   │   ├── api/              HTTP routes, schemas, dependencies
│   │   ├── application/      Business logic, services, ports
│   │   ├── domain/           Entities, repositories, value objects
│   │   └── infrastructure/   Database, storage, AI, vector store
│   ├── migrations/           Alembic database migrations
│   └── tests/                Pytest test suite
│
├── frontend/                 Next.js 16 application
│   └── src/
│       ├── app/              Route-based pages
│       └── shared/           Types, API client, UI components, store
│
├── docs/                     Technical spec, ADRs, deployment guide
├── .ai/                      AI agent context and rules
├── docker-compose.yml        Local infrastructure (Qdrant, Temporal)
└── render.yaml               Render deployment config
```

---

## Getting Started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.13
- Node.js 18+
- Docker (for local infrastructure)

### Quick Start

```bash
# 1. Clone
git clone https://github.com/nahyan0077/knowledge-os.git
cd knowledge-os

# 2. Start infrastructure (Qdrant + Temporal)
docker compose up -d

# 3. Backend
cd backend && cp .env.example .env
# Edit .env with your database URL and API keys
make setup && make run

# 4. Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000`, create an account, and upload your first document.

> **Apple Silicon:** Frontend build requires `npm run build -- --webpack`

---

## Development

### Commands

```bash
make help           # Show all commands
make setup          # Install dependencies
make run            # Start backend dev server
make test           # Run tests
make check          # Lint + typecheck
make migrate        # Run migrations
```

### Code Quality

- **Linting:** Ruff (line-length 100, Python 3.13)
- **Type checking:** mypy (strict)
- **Testing:** pytest with async support
- **Frontend:** ESLint

Run `make check` before committing.

---

## Architecture Decisions

| ADR | Decision |
|-----|----------|
| [ADR-001](docs/adr/ADR-001-modular-monolith.md) | Modular Monolith |
| [ADR-002](docs/adr/ADR-002-temporal.md) | Temporal for Durable Workflows |
| [ADR-003](docs/adr/ADR-003-postgresql-source-of-truth.md) | PostgreSQL as Source of Truth |
| [ADR-004](docs/adr/ADR-004-qdrant-derived-store.md) | Qdrant as Derived Vector Store |
| [ADR-005](docs/adr/ADR-005-pydanticai.md) | PydanticAI Behind Provider-Neutral Ports |
| [ADR-006](docs/adr/ADR-006-project-centric-hierarchy.md) | Project-Centric Hierarchy |

---

## Contributing

1. Read [.ai/PROJECT_CONTEXT.md](.ai/PROJECT_CONTEXT.md) for project overview
2. Follow [.ai/CODING_STANDARDS.md](.ai/CODING_STANDARDS.md) for code style
3. Check [docs/adr](docs/adr) before changing architecture
4. Run `make check` before committing
5. Add tests proportional to your changes

---

## License

[MIT](LICENSE)
