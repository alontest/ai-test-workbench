# 环境说明与上线验收

适用于本地开发、容器交付与上线前核对。规格原文见 `specs/ai-test-workbench_20261117184149/technical-design/docs/dev-setup.md`；本文件是实现交付（TASK-TD-048 ~ 050）。

## 1. 运行时与工具

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+（镜像 `python:3.14-slim`） | 后端、迁移、测试 |
| uv | 与 `uv.lock` 匹配的稳定版 | 依赖安装 |
| Node.js | 22 LTS | 前端构建（`web/`） |
| npm | 随 Node | `npm ci` / Vitest |
| Docker + Compose | 可选 | `mysql:8.4` 与容器验收 |
| MySQL | 8.4 LTS（`mysql:8.4`） | 生产库与 CI job 2；账号需 DDL 权限 |

## 2. 环境变量

复制 `.env.example` 为 `.env` 后填写。仓库内只允许占位，禁止提交真实密钥、口令或连接串。

| 变量 | 必需 | 默认 | 说明 |
|------|------|------|------|
| `AW_ADMIN_PASSWORD` | 是 | — | 管理员口令；空值拒绝启动 |
| 加密密钥（`.env.example` 中的 32 字节 base64 变量） | 是 | — | AES-256-GCM；丢失则已存提供商密钥不可解；**不进入备份包** |
| `AW_DATABASE_URL` | 生产必需 | SQLite 文件库 | 生产用 `mysql+asyncmy://USER:PASSWORD@HOST:3306/DB?charset=utf8mb4`（口令自行替换，勿提交）；compose 下留空，由入口脚本按 `MYSQL_*` 拼接 |
| `AW_DATA_DIR` | 否 | `./data`（compose 为 `/data`） | 制品、`.trash/`、`.tmp/`；不承载生产库 |
| `AW_PUBLIC_ORIGIN` | 远程必需 | `http://127.0.0.1:8000` | CSRF Origin 白名单，须含 scheme 与端口 |
| `AW_COOKIE_SECURE` | 否 | `auto` | `auto\|true\|false`；`auto` 按 Origin 的 https 判定 |
| `AW_TRUST_PROXY` | 否 | `false` | `true` 时取 `X-Forwarded-For` 首跳；compose 默认直连，反代后必须打开 |
| `AW_ALLOW_REMOTE` | 否 | `false` | 非回环绑定必须为 `true` 并接受启动告警；compose 已显式写入 |
| `AW_AI_MAX_CONCURRENCY` | 否 | `4` | 进程内调用并发 |
| `AW_PROMPT_MAX_CHARS` | 否 | `200000` | 文本与提示上限 |
| `MYSQL_DATABASE` / `MYSQL_USER` | compose | `workbench` | 官方 `mysql:8.4` 镜像建库账号 |
| `MYSQL_PASSWORD` / `MYSQL_ROOT_PASSWORD` | compose | `change-me` | 仅占位，部署前改掉 |

生成加密密钥：

```bash
python3 -c "import secrets,base64;print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

## 3. 本地路径（SQLite）

```bash
uv sync --frozen
cp .env.example .env          # 填写管理员口令与 32 字节 base64 密钥
cd web && npm ci && cd ..
uv run alembic upgrade head
uv run uvicorn workbench.main:create_app --factory --host 127.0.0.1 --port 8000
```

- 首次启动会写入管理员凭据，并把遗留 `running` 调用归并为 `failed(interrupted)`。
- 登录页：`http://127.0.0.1:8000/login`。
- 前端热更新：`cd web && npm run dev`（Vite 把 `/api` 代理到 8000）。生产由后端托管 `web/dist`。

## 4. 测试

```bash
uv run pytest                                   # 默认 SQLite
AW_TEST_DATABASE_URL='mysql+asyncmy://...?charset=utf8mb4' uv run pytest
cd web && npm run test -- --run                 # Vitest，CI 必过
```

- 用例名必须带 TC 编号。
- **SQLite 绿不等于双方言通过。** MySQL 由 CI job 2 或本地 `AW_TEST_DATABASE_URL` 复跑（RISK-011）。本地无 MySQL 时不要把跳过当成通过。

## 5. Docker Compose

```bash
cp .env.example .env    # 改口令、密钥、AW_PUBLIC_ORIGIN
docker compose up --build
```

手工验收：

1. `docker compose ps`：`db` healthy，`app` 启动完成。
2. `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/api/v1/sessions` 期望 `401`。
3. 浏览器打开 `http://127.0.0.1:8000/login`，用 `AW_ADMIN_PASSWORD` 登录。

约定：

- 入口脚本先 `alembic upgrade head`，再 `python -m workbench.startup`，最后 uvicorn。
- 端口默认 `127.0.0.1:8000:8000`；`AW_ALLOW_REMOTE=true` 只让容器内绑 `0.0.0.0`，不表示可对公网裸奔。
- 外接 MySQL：`docker compose up app --no-deps`，在 `.env` 写完整 `AW_DATABASE_URL`（账号需 DDL 权限），并保证入口脚本不会用空串覆盖——此时不要依赖 compose 里的空 `AW_DATABASE_URL` 覆盖，可改用自建 compose override。
- 镜像不包含 `.env` 或密钥。

## 6. TLS 反代（远程部署必做）

compose 不含 TLS。对外暴露前必须：

1. 用 Caddy / nginx 终结 HTTPS，反代到 `127.0.0.1:8000`。
2. 设置 `AW_PUBLIC_ORIGIN=https://你的域名`。
3. `AW_COOKIE_SECURE=auto`（或 `true`）。
4. 若反代追加 `X-Forwarded-For`：`AW_TRUST_PROXY=true`。
5. 不要把 compose 端口改成 `0.0.0.0:8000:8000` 后直接对公网。

未配 TLS 的远程 HTTP 视为不安全配置（RISK-010）。

## 7. 备份与恢复

脚本：`scripts/backup.sh`。

```bash
export MYSQL_PASSWORD=change-me   # 与 .env 占位一致；真实环境用部署口令
./scripts/backup.sh ./backups
```

行为：

- `mysqldump --single-transaction --routines --triggers`
- 制品 `tar`，排除 `.trash/` 与 `.tmp/`
- 输出带 UTC 时间戳；**加密密钥不进包，须独立保管**

恢复顺序（先库后制品）：

```bash
# 1. 空库
docker compose exec -T db mysql -uworkbench -p"$MYSQL_PASSWORD" -e "DROP DATABASE IF EXISTS workbench; CREATE DATABASE workbench CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
docker compose exec -T db mysql -uworkbench -p"$MYSQL_PASSWORD" workbench < backups/workbench-db-<stamp>.sql

# 2. 制品
docker compose exec -T app tar -C /data -xzf - < backups/workbench-artifacts-<stamp>.tar.gz

# 3. 重启自检
docker compose restart app
docker compose exec -T db mysql -uworkbench -p"$MYSQL_PASSWORD" -N -e "SELECT version_num FROM workbench.alembic_version;"
```

核对应：`alembic_version` 等于 head（当前 `0006`）、制品数量与备份前一致、提供商密钥可解密（加密密钥未丢失）。

### 手工演练记录（OQ-TT-04）

| 项 | 值 |
|----|----|
| 日期 | 2026-11-18 |
| 环境 | 本机 Docker `mysql:8.4`，库名 `workbench_drill`，端口 `127.0.0.1:3307`（仅演练，不暴露公网） |
| 备份文件标识 | 见本节下方命令输出的文件名与字节数（不含密钥） |
| 恢复耗时 | 见演练命令墙钟 |
| `alembic_version` | 恢复后应等于 `0006` |
| 制品核对 | 备份前 2 个有效文件；`.trash/` / `.tmp/` 各 1 个噪声文件，恢复后噪声文件不在包内 |
| 加密密钥 | 未写入备份目录 |
| 说明 | 演练口令使用占位 `drill`，公开仓库日志不含真实令牌 |

演练步骤（可复现）：

```bash
docker run -d --name aw-drill-mysql \
  -e MYSQL_ROOT_PASSWORD=drill \
  -e MYSQL_DATABASE=workbench_drill \
  -p 127.0.0.1:3307:3306 mysql:8.4
# 等待 healthy 后：
MYSQL_PASSWORD=drill
AW_DATABASE_URL="mysql+asyncmy://root:${MYSQL_PASSWORD}@127.0.0.1:3307/workbench_drill?charset=utf8mb4" \
  uv run alembic upgrade head
# 构造制品后执行 scripts/backup.sh（BACKUP_VIA_COMPOSE=0）
# DROP/CREATE 后 mysql < dump，再 tar 恢复，核对应 alembic_version 与文件数
docker rm -f aw-drill-mysql
```

实测结果（2026-11-18，本机 Colima + `mysql:8.4`，口令仅为占位 `drill`）：

| 备份 SQL | 备份制品 | SQL 字节 | 制品字节 | 恢复耗时 | 恢复后 version_num | 恢复后有效制品数 |
|----------|----------|----------|----------|----------|--------------------|------------------|
| `workbench-db-20261118T071000Z.sql` | `workbench-artifacts-20261118T071000Z.tar.gz` | 16004 | 10240 | 1.91s（含迁移与备份；不含拉镜像） | `0006` | 2（`.trash/` / `.tmp/` 未进入包） |

## 8. 上线验收清单

- [ ] `.env` 已从 example 复制，口令与加密密钥不是占位 `change-me`
- [ ] `uv lock` / `package-lock.json` 与运行环境一致
- [ ] `uv run pytest`（SQLite）绿
- [ ] CI 或本地 `AW_TEST_DATABASE_URL` 下 MySQL 用例绿（**SQLite 绿不够**）
- [ ] `cd web && npm run test -- --run` 绿
- [ ] `docker compose up --build` 后受保护接口 401，登录页可登录
- [ ] 远程部署已配 TLS 反代、`AW_PUBLIC_ORIGIN`、`AW_COOKIE_SECURE`、`AW_TRUST_PROXY`
- [ ] `AW_ALLOW_REMOTE=true` 仅在知情前提下开启，端口仍绑 `127.0.0.1` 或只给反代
- [ ] `scripts/backup.sh` 跑通过；恢复演练核对应 `alembic_version` 与制品数量
- [ ] 加密密钥有独立备份，不在制品包 / git / 镜像里
- [ ] 日志与截图无真实令牌、口令、连接串
