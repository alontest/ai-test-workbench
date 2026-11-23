# Vigil · 鸮巡

单用户自托管 AI 测试工作台：登录后建项目、配模型、开会话、贴文本/上传制品并调用模型，结果留在时间线与调用记录里。

## 快速开始

本地（SQLite）：

```bash
uv sync --frozen
cp .env.example .env          # 填写口令与 32 字节 base64 加密密钥
uv run alembic upgrade head
cd web && npm ci && npm run build && cd ..
uv run uvicorn vigil_workbench.main:create_app --factory --host 127.0.0.1 --port 8000
```

容器（MySQL 8.4）：

```bash
cp .env.example .env
docker compose up --build     # 默认 127.0.0.1:8000
```

完整环境变量、测试、TLS 反代、备份恢复与上线清单见 [`docs/dev-setup.md`](docs/dev-setup.md)。

## 开发

规格驱动开发，阶段产物写在 `specs/<module>_<timestamp>/`。开发约定、构建命令与仓库不变量见 [`AGENTS.md`](AGENTS.md)。

```bash
uv run pytest -q                                # 后端，默认 SQLite
cd web && npm run test -- --run                 # 前端 Vitest
```

**SQLite 绿不等于双方言通过。** 生产用 MySQL 8.4；远程部署必须 TLS 反代，compose 默认不对公网裸奔。
