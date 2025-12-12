# Meridian Backend Overview

## Purpose
FastAPI service that brokers authentication, chat threads, message storage, and orchestrates calls to the agents service.

## Entry Points
- `server.py`: FastAPI app creation, middleware, and router registration.
- `api/health.py`: liveness/readiness endpoints.
- `api/chat.py`, `api/messages.py`, `api/threads.py`: chat/message REST endpoints.
- `api/agents.py`: proxy to agents service.
- `services/*`: business logic for chat, messages, query classification, and agent orchestration.
- `database/*`: Cloud SQL client, migrations, CRUD helpers.
- `models/*`: Pydantic request/response schemas and internal models.

## Data & Dependencies
- Persistence via Cloud SQL; migrations in `database/migrations/`.
- External calls to agents service via HTTP.
- Config via `utils/config.py` (env vars for DB and service URLs).

## Observability
- Structured logging configured in `server.py`.
- Request IDs added via middleware for trace correlation across services.

