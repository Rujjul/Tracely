#!/bin/sh
set -eu
cd "$(dirname "$0")/../../backend"
: "${DATABASE_URL:?Set DATABASE_URL in the Render environment settings}"
# Never print migration tracebacks that could include connection details or data.
if ! python -m alembic upgrade head >/dev/null 2>&1; then
    echo 'Database migration failed. Check Neon connectivity and migration compatibility using a secure administrator session.' >&2
    exit 1
fi
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 --no-access-log --no-proxy-headers
