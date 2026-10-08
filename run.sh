#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PYTHON=python3
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON=python3.12
fi
exec "$PYTHON" run.py "$@"
