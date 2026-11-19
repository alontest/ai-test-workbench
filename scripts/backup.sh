#!/usr/bin/env bash
# 备份 MySQL（mysqldump --single-transaction --routines --triggers）与制品目录。
# 排除 .trash/、.tmp/；不打包加密密钥。恢复顺序：先库后制品。
set -euo pipefail

usage() {
  cat <<'EOF'
用法: scripts/backup.sh [备份目录]

环境变量:
  BACKUP_DIR          备份输出目录（也可用第一个参数）
  MYSQL_HOST          仅本地 mysqldump 时需要（默认 127.0.0.1）
  MYSQL_PORT          默认 3306
  MYSQL_USER          默认 workbench
  MYSQL_PASSWORD      必填（本地 mysqldump）
  MYSQL_DATABASE      默认 workbench
  MYSQL_ROOT_PASSWORD compose 路径下传给 db 容器（可选）
  MYSQL_CONTAINER     若设置，则 docker exec 该容器跑 mysqldump（演练/无 compose 时）
  AW_DATA_DIR         制品目录（非 compose 路径；默认 ./data）
  BACKUP_VIA_COMPOSE  1=优先 docker compose exec（默认 1）
  COMPOSE_FILE        默认仓库根 docker-compose.yml

恢复（手工）:
  1. 保管 AW_ENCRYPTION_KEY，不要放进备份包。
  2. 先导入 SQL，再解压制品到 AW_DATA_DIR。
  3. 启动自检，核对应 alembic_version 与制品数量。
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${1:-${BACKUP_DIR:-$ROOT/backups}}"
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-workbench}"
MYSQL_DATABASE="${MYSQL_DATABASE:-workbench}"
AW_DATA_DIR="${AW_DATA_DIR:-$ROOT/data}"
BACKUP_VIA_COMPOSE="${BACKUP_VIA_COMPOSE:-1}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.yml}"

mkdir -p "$BACKUP_DIR"
SQL_PATH="$BACKUP_DIR/workbench-db-$STAMP.sql"
ARTIFACT_PATH="$BACKUP_DIR/workbench-artifacts-$STAMP.tar.gz"
MANIFEST_PATH="$BACKUP_DIR/workbench-backup-$STAMP.txt"

dump_via_compose() {
  docker compose -f "$COMPOSE_FILE" exec -T db \
    mysqldump --single-transaction --routines --triggers \
    -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"
}

dump_via_container() {
  docker exec -i "$MYSQL_CONTAINER" \
    mysqldump --single-transaction --routines --triggers \
    -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"
}

archive_via_compose() {
  docker compose -f "$COMPOSE_FILE" exec -T app \
    tar -C /data --exclude='.trash' --exclude='.tmp' -czf - .
}

dump_local() {
  mysqldump --single-transaction --routines --triggers \
    -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" \
    "$MYSQL_DATABASE"
}

archive_local() {
  tar -C "$AW_DATA_DIR" --exclude='.trash' --exclude='.tmp' -czf - .
}

compose_service_running() {
  local service="$1"
  [[ "$BACKUP_VIA_COMPOSE" == "1" ]] \
    && command -v docker >/dev/null \
    && [[ -n "$(docker compose -f "$COMPOSE_FILE" ps --status running -q "$service" 2>/dev/null || true)" ]]
}

if [[ -z "${MYSQL_PASSWORD:-}" ]]; then
  echo "MYSQL_PASSWORD 未设置。" >&2
  exit 2
fi

METHOD="local"
if compose_service_running db; then
  METHOD="compose"
  dump_via_compose >"$SQL_PATH"
elif [[ -n "${MYSQL_CONTAINER:-}" ]]; then
  METHOD="container"
  dump_via_container >"$SQL_PATH"
else
  if ! command -v mysqldump >/dev/null 2>&1; then
    echo "未找到 mysqldump，且 compose db 未运行。" >&2
    exit 3
  fi
  dump_local >"$SQL_PATH"
fi

if compose_service_running app; then
  archive_via_compose >"$ARTIFACT_PATH"
else
  if [[ ! -d "$AW_DATA_DIR" ]]; then
    echo "AW_DATA_DIR 不存在: $AW_DATA_DIR" >&2
    exit 4
  fi
  archive_local >"$ARTIFACT_PATH"
fi

{
  echo "stamp=$STAMP"
  echo "method=$METHOD"
  echo "database=$MYSQL_DATABASE"
  echo "sql=$(basename "$SQL_PATH")"
  echo "artifacts=$(basename "$ARTIFACT_PATH")"
  echo "sql_bytes=$(wc -c <"$SQL_PATH" | tr -d ' ')"
  echo "artifact_bytes=$(wc -c <"$ARTIFACT_PATH" | tr -d ' ')"
  echo "note=AW_ENCRYPTION_KEY is NOT included; keep it separately."
} >"$MANIFEST_PATH"

echo "backup written:"
echo "  $SQL_PATH"
echo "  $ARTIFACT_PATH"
echo "  $MANIFEST_PATH"
echo "Keep AW_ENCRYPTION_KEY outside this directory."
