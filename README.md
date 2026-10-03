# ApprovalFlow Agent

[![CI](https://github.com/Jemade/Human-in-the-loop/actions/workflows/ci.yml/badge.svg)](https://github.com/Jemade/Human-in-the-loop/actions/workflows/ci.yml)

A Python workflow application that separates drafting and planning from consequential external actions. Operators inspect proposed actions and approve or reject them through a browser interface.

## Features

- Database-backed workflow states and approval records.
- Tool risk classification and an explicit approval gate.
- Idempotency protection and an audit trail.
- Outreach drafting and an inspectable sandbox outbox.
- Heuristic, OpenAI, Anthropic, and Gemini provider options.
- SQLite development storage and PostgreSQL configuration.

## Run locally

```bash
git clone https://github.com/Jemade/Human-in-the-loop.git
cd Human-in-the-loop
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Open http://localhost:8001 for the interface and http://localhost:8001/docs for the API.

Default configuration uses `LLM_PROVIDER=heuristic` and `EMAIL_PROVIDER=sandbox`, so the demo does not send email. The heuristic path creates demonstration research and drafts, not verified web research.

Use `.env.example` as a reference. To enable authentication, set `REQUIRE_AUTH=true` and replace `API_KEY` with your own secret. Configure provider credentials for live generation. SMTP delivery requires SMTP configuration and the corresponding provider selection.

## Containers and tests

```bash
docker compose up --build
pytest -q
```

The Compose configuration is a development setup. Review its authentication and secret settings before public deployment.

## Code map

- `app/`: API, workflow state, tool execution, and providers.
- `app/ui/`: approval interface.
- `tests/`: workflow and safety checks.

## Current scope

Approval controls govern registered actions in this application. They do not independently verify the factual accuracy of a model-generated draft or research result.
