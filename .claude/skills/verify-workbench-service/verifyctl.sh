#!/usr/bin/env bash
# verifyctl — 启动 / 体检 / 驱动 / 停止一个隔离的 workbench 实例。
#
# 用法（在仓库任意位置执行）：
#   .claude/skills/verify-workbench-service/verifyctl.sh start  <run-id>
#   .claude/skills/verify-workbench-service/verifyctl.sh doctor <run-id>
#   .claude/skills/verify-workbench-service/verifyctl.sh req    <run-id> <path> [curl args...]
#   .claude/skills/verify-workbench-service/verifyctl.sh sql    <run-id> "<SQL>"
#   .claude/skills/verify-workbench-service/verifyctl.sh seed-running <run-id>
#   .claude/skills/verify-workbench-service/verifyctl.sh stop   <run-id>
#
# 状态目录：<repo>/.verify/run/<run-id>/      证据目录：<repo>/.verify/evidence/<run-id>/
# 同一 run-id 再次 start 即“重启”，数据目录与端口保持不变。

set -euo pipefail

CMD="${1:-}"
RUN_ID="${2:-}"
if [[ -z "$CMD" || -z "$RUN_ID" ]]; then
  echo "usage: verifyctl.sh <start|doctor|req|sql|seed-running|stop> <run-id>" >&2
  exit 64
fi

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
RUN_DIR="$ROOT/.verify/run/$RUN_ID"
EVID_DIR="$ROOT/.verify/evidence/$RUN_ID"
ENV_FILE="$RUN_DIR/env.sh"
PID_FILE="$RUN_DIR/uvicorn.pid"
PORT_FILE="$RUN_DIR/port"
LOG_FILE="$RUN_DIR/uvicorn.log"
PY="$ROOT/.venv/bin/python"
ALEMBIC="$ROOT/.venv/bin/alembic"
UVICORN="$ROOT/.venv/bin/uvicorn"
READY_PATH="/api/v1/__verify_ready"   # 未登录拦截返回 401 即代表应用与鉴权中间件在服务
READY_TIMEOUT_SECONDS=60

die() { echo "FAIL: $*" >&2; exit 1; }

free_port() {
  "$PY" - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

load_env() {
  [[ -f "$ENV_FILE" ]] || die "no run '$RUN_ID'; run start first"
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  PORT="$(cat "$PORT_FILE")"
  export PORT
}

pid_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

cmd_start() {
  mkdir -p "$RUN_DIR" "$EVID_DIR"

  if [[ -f "$PORT_FILE" ]]; then
    PORT="$(cat "$PORT_FILE")"
  else
    PORT="$(free_port)"
    echo "$PORT" > "$PORT_FILE"
  fi

  if [[ ! -f "$ENV_FILE" ]]; then
    local key repo_key
    key="$("$PY" -c 'import base64,os;print(base64.b64encode(os.urandom(32)).decode())')"
    repo_key="$("$PY" -c 'import base64,os;print(base64.b64encode(os.urandom(32)).decode())')"
    cat > "$ENV_FILE" <<EOF
export VIGIL_ADMIN_PASSWORD='verify-ephemeral-admin'
export VIGIL_ENCRYPTION_KEY='$key'
export VIGIL_REPO_TOKEN_KEY='$repo_key'
export VIGIL_DATA_DIR='$RUN_DIR/data'
export VIGIL_DATABASE_URL='sqlite+aiosqlite:///$RUN_DIR/data/vigil.db'
export VIGIL_PUBLIC_ORIGIN='http://127.0.0.1:$PORT'
export VIGIL_COOKIE_SECURE='false'
EOF
  fi
  load_env
  mkdir -p "$VIGIL_DATA_DIR"

  if pid_alive "$(cat "$PID_FILE" 2>/dev/null || true)"; then
    echo "already running (pid $(cat "$PID_FILE")) at $VIGIL_PUBLIC_ORIGIN"
    return 0
  fi

  ( cd "$ROOT" && "$ALEMBIC" upgrade head ) >"$RUN_DIR/alembic.log" 2>&1 \
    || die "alembic upgrade head failed; see $RUN_DIR/alembic.log"
  ( cd "$ROOT" && "$PY" -m vigil_workbench.startup ) >"$RUN_DIR/startup.log" 2>&1 \
    || die "startup self-check failed; see $RUN_DIR/startup.log"

  ( cd "$ROOT" && exec "$UVICORN" --factory vigil_workbench.main:create_app \
      --host 127.0.0.1 --port "$PORT" --log-level info ) >"$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"

  local i code
  for ((i = 0; i < READY_TIMEOUT_SECONDS * 4; i++)); do
    if ! pid_alive "$(cat "$PID_FILE")"; then
      tail -20 "$LOG_FILE" >&2
      die "uvicorn exited during startup"
    fi
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:$PORT$READY_PATH" || true)"
    if [[ "$code" != "000" ]]; then
      echo "running: pid $(cat "$PID_FILE")  url $VIGIL_PUBLIC_ORIGIN  http $code"
      return 0
    fi
    sleep 0.25
  done
  tail -20 "$LOG_FILE" >&2
  die "uvicorn not answering on 127.0.0.1:$PORT after ${READY_TIMEOUT_SECONDS}s"
}

cmd_doctor() {
  load_env
  local pid alive="" owner version code hdr
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  pid_alive "$pid" && alive="yes" || alive="no"
  owner="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | tr '\n' ' ' || true)"
  version="$(sqlite3 "$VIGIL_DATA_DIR/vigil.db" 'SELECT version_num FROM alembic_version' 2>/dev/null || true)"
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:$PORT$READY_PATH" || true)"
  hdr="$(curl -sS -o /dev/null -D - --max-time 2 "http://127.0.0.1:$PORT$READY_PATH" 2>/dev/null | tr -d '\r' | awk 'tolower($1)=="x-request-id:"{print $2}' || true)"

  echo "run:        $RUN_ID"
  echo "url:        http://127.0.0.1:$PORT"
  echo "data dir:   $VIGIL_DATA_DIR"
  echo "pid:        ${pid:-<none>} (alive: $alive)"
  echo "port owner: ${owner:-<none>}"
  echo "alembic:    ${version:-<none>} (expect 0009)"
  echo "http:       ${code:-<none>} (expect 401 from the auth-guarded readiness path)"
  echo "request-id: ${hdr:-<none>}"

  [[ "$alive" == "yes" ]] || die "process not alive"
  [[ "$owner" == *"$pid"* ]] || die "port $PORT is not owned by our pid $pid"
  [[ "$version" == "0009" ]] || die "alembic head is $version, expected 0009"
  [[ "$code" == "401" ]] || die "readiness path returned $code, expected 401"
  [[ -n "$hdr" ]] || die "response carries no X-Request-Id"
  echo "OK"
}

cmd_req() {
  load_env
  local path="${3:-}"
  shift 3 2>/dev/null || true
  [[ -n "$path" ]] || die "usage: req <run-id> <path> [curl args...]"
  curl -sS -i --max-time 10 "$@" "http://127.0.0.1:$PORT$path"
}

cmd_sql() {
  load_env
  local query="${3:-}"
  [[ -n "$query" ]] || die "usage: sql <run-id> \"<SQL>\""
  sqlite3 -header -column "$VIGIL_DATA_DIR/vigil.db" "$query"
}

cmd_seed_running() {
  load_env
  ( cd "$ROOT" && "$PY" - "$VIGIL_DATA_DIR/vigil.db" <<'PY'
import asyncio
import sys
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from vigil_workbench.db.base import utcnow
from vigil_workbench.db.models import (
    AiCallRecord, AnalysisSession, ModelBinding, ProjectContext, ProviderConfig,
)

async def main(db_path: str) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        project = ProjectContext(name="verify-project", name_key="verify-project")
        db.add(project)
        await db.flush()
        provider = ProviderConfig(
            name="verify-provider", protocol="openai_compatible",
            base_url="https://api.example.invalid/v1",
            api_key_ciphertext="unused-in-verification", enabled=True,
        )
        db.add(provider)
        await db.flush()
        model = ModelBinding(
            provider_id=provider.provider_id, model_name="verify-model",
            model_name_key="verify-model", display_name="Verify Model",
            default_temperature=Decimal("0.70"), default_max_tokens=4096, enabled=True,
        )
        db.add(model)
        await db.flush()
        session = AnalysisSession(
            project_id=project.project_id, entrance_key="case-library",
            title="verify: interrupted call", model_id=model.model_id,
        )
        db.add(session)
        await db.flush()
        record = AiCallRecord(
            session_id=session.session_id, model_id=model.model_id,
            provider_id=provider.provider_id, model_name_snapshot="verify-model",
            display_name_snapshot="Verify Model", provider_name_snapshot="verify-provider",
            protocol_snapshot="openai_compatible", status="running",
            prompt_digest="0" * 64, prompt_preview="verify", prompt_char_count=6,
            created_at=utcnow() - timedelta(seconds=5),
        )
        db.add(record)
        await db.commit()
        print(f"session_id={session.session_id} call_id={record.call_id}")
    await engine.dispose()

asyncio.run(main(sys.argv[1]))
PY
  )
}

cmd_stop() {
  load_env
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if ! pid_alive "$pid"; then
    echo "no live pid recorded in $PID_FILE"
    return 0
  fi
  kill "$pid"
  local i
  for ((i = 0; i < 40; i++)); do
    pid_alive "$pid" || break
    sleep 0.25
  done
  if pid_alive "$pid"; then
    kill -9 "$pid" || true
  fi
  rm -f "$PID_FILE"
  echo "stopped pid $pid; evidence kept in $EVID_DIR"
}

case "$CMD" in
  start)        cmd_start ;;
  doctor)       cmd_doctor ;;
  req)          cmd_req "$@" ;;
  sql)          cmd_sql "$@" ;;
  seed-running) cmd_seed_running ;;
  stop)         cmd_stop ;;
  *)            die "unknown command '$CMD'" ;;
esac
