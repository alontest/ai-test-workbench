#!/bin/sh
set -eu

cd /app
export PATH="/app/.venv/bin:${PATH}"

if [ "${1:-}" = "healthcheck" ]; then
  python - <<'PY'
import sys
import urllib.error
import urllib.request

try:
    urllib.request.urlopen("http://127.0.0.1:8000/api/v1/sessions", timeout=3)
except urllib.error.HTTPError as exc:
    sys.exit(0 if exc.code == 401 else 1)
except Exception:
    sys.exit(1)
else:
    sys.exit(1)
PY
  exit $?
fi

if [ -z "${VIGIL_DATABASE_URL:-}" ]; then
  user="${MYSQL_USER:-vigil}"
  pass="${MYSQL_PASSWORD:-change-me}"
  name="${MYSQL_DATABASE:-vigil}"
  host="${MYSQL_HOST:-db}"
  port="${MYSQL_PORT:-3306}"
  VIGIL_DATABASE_URL="mysql+asyncmy://${user}:${pass}@${host}:${port}/${name}?charset=utf8mb4"
  export VIGIL_DATABASE_URL
fi

echo "alembic upgrade head"
alembic upgrade head

echo "startup self-check"
python -m vigil_workbench.startup

allow="${VIGIL_ALLOW_REMOTE:-false}"
case "$allow" in
  1|true|TRUE|yes|YES)
    echo "WARNING: VIGIL_ALLOW_REMOTE is enabled; binding 0.0.0.0. Put a TLS reverse proxy in front and set VIGIL_PUBLIC_ORIGIN / VIGIL_COOKIE_SECURE." >&2
    host="0.0.0.0"
    ;;
  *)
    host="127.0.0.1"
    ;;
esac

set -- uvicorn vigil_workbench.main:create_app --factory --host "$host" --port 8000
trust="${VIGIL_TRUST_PROXY:-false}"
case "$trust" in
  1|true|TRUE|yes|YES)
    set -- "$@" --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}"
    ;;
esac

exec "$@"
