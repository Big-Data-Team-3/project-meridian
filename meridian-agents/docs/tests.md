# Agents Tests

## Commands
- Install deps: `pip install -r requirements.txt`
- Unit + integration: `cd /Users/smatcha/Documents/BigData/project-meridian/meridian-agents && pytest -v`
- Targeted integration: `pytest tests/integration/ -v`
- Full agent sweep: `bash /Users/smatcha/Documents/BigData/project-meridian/scripts/test_all_agents.sh AAPL $(date +%Y-%m-%d)`

## Coverage Focus
- `graph/*`: planner/orchestrator signal routing.
- `agents_module/*`: persona behaviors and tool bindings.
- `dataflows/*`: API adapters for market/news/social data.
- `utils/*`: logging, streaming, SSE formatting.
- `models/*`: request/response schema validation.

## Env Requirements
- `OPENAI_API_KEY` required for most integration and eval flows.
- Network access to configured data providers (Alpha Vantage, YFinance, Google News, Reddit/Twitter where applicable).

## Integration Notes
- Keep eval and integration tests deterministic by pinning tickers/dates where possible.
- Use `pytest -k "not slow"` when skipping expensive tests in local dev or CI without credentials.

