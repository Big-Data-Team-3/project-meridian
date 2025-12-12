# Backend Tests

## Commands
- Install deps: `pip install -r requirements.txt`
- Unit + integration: `cd /Users/smatcha/Documents/BigData/project-meridian/meridian-backend && pytest -v`
- Targeted DB tests: `python database/test_connection.py` and `python database/test_crud_operations.py`
- Lint (optional if configured): `python -m ruff .` (add to CI when ready)

## Coverage Focus
- `services/*`: chat/message orchestration, agent delegation.
- `api/*`: request/response validation and error handling.
- `database/*`: Cloud SQL client, migrations, CRUD operations.
- `models/*`: schema validation and intent classification.

## Env Requirements
- DB settings: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_TYPE` (postgresql).
- GCP auth: `GOOGLE_APPLICATION_CREDENTIALS` for Cloud SQL access.
- Agents service URL: `AGENTS_SERVICE_URL` when running integration tests.

## Integration Notes
- Run migrations (`python database/run_migrations.py`) before DB tests.
- Mark integration tests that require external services to allow CI gating if secrets are missing.

