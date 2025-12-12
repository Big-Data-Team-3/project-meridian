# Meridian Agents Overview

## Purpose
FastAPI service orchestrating multi-agent financial analysis using OpenAI Agents SDK and LangGraph. Provides the `/analyze` endpoint consumed by the backend and frontend.

## Entry Points
- `server.py`: FastAPI app, routing, and middleware.
- `graph/*`: LangGraph orchestration, planners, orchestrator, and signal processing.
- `agents_module/*`: agent personas (analysts, researchers, managers, debaters) and registry files.
- `dataflows/*`: market/news/social data ingestion, indicator calculations, and OpenAI wrappers.
- `models/*`: request/response schemas for agent workflows.

## Data & Config
- Configuration via environment variables (`OPENAI_API_KEY`, `PORT`, `LOG_LEVEL`, `ENVIRONMENT`).
- Data caches under `dataflows/data_cache/`.
- Registry JSON files define tool/agent capabilities.

## Observability
- Structured JSON logging in `utils/logging.py`.
- Health endpoint in `tests/test_health.py` ensures readiness.

