#!/usr/bin/env bash
set -e

echo "Starting ApprovalFlow Agent..."
export PYTHONPATH=.

if [ -d ".venv" ]; then
    .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
else
    uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
fi
