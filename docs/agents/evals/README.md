# Agent Evaluation Playbook

## Goal
Provide repeatable evaluations for agent behaviors, safety, and output quality across market scenarios.

## What We Evaluate
- Response correctness vs. ground truth tickers/dates.
- Safety: hallucination checks, cost/latency limits, and content policy adherence.
- Debate stability: convergence of bull/bear debates and risk assessments.

## Artifacts
- Datasets: store under `docs/agents/evals/data/` (CSV/JSON with ticker, date, expected signals). Include checksums in a sibling `checksums.txt`.
- Prompts/Rubrics: keep in `docs/agents/evals/prompts/` describing scoring criteria.
- Results: commit summaries under `docs/agents/evals/results/` with run date, dataset, and scores.

## How to Run
```bash
# Unit + integration tests (agents service)
cd /Users/smatcha/Documents/BigData/project-meridian/meridian-agents
pytest -v

# Full agent sweep (uses OpenAI + data providers)
bash /Users/smatcha/Documents/BigData/project-meridian/scripts/test_all_agents.sh AAPL 2025-12-12

# Trigger eval workflow in CI (manual dispatch)
gh workflow run eval.yml -f ticker=AAPL -f date=2025-12-12
```

## CI Integration
- Workflow: `.github/workflows/eval.yml`
- Inputs: `ticker` (default AAPL), `date` (default today).
- Secrets: `OPENAI_API_KEY`, plus any provider keys required by dataflows.
- Fails build on any agent test failure; attach logs for debugging.

## PR Expectations
- Include latest eval run link (CI job URL) when modifying agent logic.
- Update this README when adding datasets/prompts or changing scoring.

