# Project File Structure — ai-test-workbench（workbench-core）

> 阶段：tech-tasks（步骤 7）。依据 `technical-design/change-spec.md` §2、`docs/component-tree.md`、`docs/api-spec.md`、`docs/database-schema.md`。
> 仓库现状：`pyproject.toml` 仅占位、`src/workbench/__init__.py` 只有版本号、`tests/conftest.py` 为空；本结构从零建立，不保留占位内容（`tests/conftest.py` 改造成 fixture 入口）。

## 技术栈

- 后端：Python 3.12+ / FastAPI 0.163 / Uvicorn 0.54 / Pydantic 2.14 / SQLAlchemy 2.1 async / Alembic 1.20 / aiosqlite（开发测试）/ asyncmy（MySQL 8.4 生产）。
- 安全：argon2-cffi（口令）、cryptography AES-256-GCM（提供商密钥）、SHA-256（令牌与来源 IP 哈希）。
- AI：openai 3.52（`base_url` 兼容）与 anthropic 2.9 官方 SDK，统一封装在 `AiGateway`。
- 前端：React 19.3 + TypeScript 7.0 + Vite 8.3 + React Router 8.5 + TanStack Query 5.107 + Radix Primitives 1.8 + CSS Modules。
- 测试：pytest + pytest-asyncio + httpx `ASGITransport`；前端 Vitest/Playwright 为 P1 可选，不进门禁。

## 目录结构

```text
ai-test-workbench/
├── pyproject.toml                       # 依赖、pytest 配置（TASK-TD-001）
├── uv.lock                              # 后端精确版本锁定
├── alembic.ini                          # 迁移入口（TASK-TD-009）
├── .env.example                         # AW_* 环境变量清单，不含真实值
├── .dockerignore
├── Dockerfile                           # 多阶段：Node 构建 web/dist → Python 运行
├── docker-compose.yml                   # app + mysql:8.4；端口默认 127.0.0.1
├── README.md                            # 启动入口，指向 docs/dev-setup.md
├── migrations/
│   ├── env.py                           # 双方言、batch 模式、naming_convention
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_auth.py                 # admin_credential / login_session / login_attempt
│       ├── 0002_project_provider_model.py
│       ├── 0003_session_event.py
│       ├── 0004_artifact.py
│       └── 0005_ai_call_record.py
├── scripts/
│   ├── docker-entrypoint.sh             # alembic upgrade head 后启动 uvicorn
│   └── backup.sh                        # mysqldump + 制品打包
├── src/workbench/
│   ├── __init__.py                      # 包入口与版本号
│   ├── main.py                          # create_app()：路由、静态托管、异常处理、生命周期
│   ├── config.py                        # pydantic-settings，AW_* 与启动校验
│   ├── startup.py                       # 启动自检顺序、running 归并、清理任务
│   ├── core/
│   │   ├── constants.py                 # 200000/10MB/10/120s/10s/8h/5 次等常量
│   │   ├── entrances.py                 # 6 入口唯一来源（key/name/description/domain/status）
│   │   ├── crypto.py                    # AES-256-GCM、掩码、解密错误
│   │   ├── password.py                  # Argon2 哈希与校验
│   │   └── redaction.py                 # 日志脱敏过滤器
│   ├── db/
│   │   ├── base.py                      # Declarative Base、naming_convention、类型助手
│   │   ├── engine.py                    # 双方言引擎与连接池
│   │   ├── models/                      # 每表一个模块（10 个）
│   │   │   ├── admin_credential.py
│   │   │   ├── login_session.py
│   │   │   ├── login_attempt.py
│   │   │   ├── project_context.py
│   │   │   ├── provider_config.py
│   │   │   ├── model_binding.py
│   │   │   ├── analysis_session.py
│   │   │   ├── session_event.py
│   │   │   ├── artifact.py
│   │   │   └── ai_call_record.py
│   │   └── repositories/                # 查询封装，不写业务规则
│   │       ├── auth.py
│   │       ├── projects.py
│   │       ├── providers.py
│   │       ├── models.py
│   │       ├── sessions.py
│   │       ├── events.py
│   │       ├── artifacts.py
│   │       └── calls.py
│   ├── services/
│   │   ├── errors.py                    # DomainError 与错误码
│   │   ├── auth.py                      # 登录、令牌、锁定、登出
│   │   ├── projects.py
│   │   ├── providers.py                 # 加密存储、掩码、连接测试
│   │   ├── models.py
│   │   ├── sessions.py                  # 冻结：create / append_event
│   │   ├── artifacts.py                 # 冻结：save
│   │   ├── calls.py                     # 调用记录查询
│   │   └── ai_gateway.py                # 冻结：AiGateway.complete
│   ├── adapters/
│   │   ├── ai/
│   │   │   ├── base.py                  # ProtocolAdapter、AIResult、AIError
│   │   │   ├── openai_compatible.py
│   │   │   └── anthropic.py
│   │   └── fs/
│   │       └── storage.py               # 临时文件、原子移动、包含校验、trash、孤儿扫描
│   └── api/
│       ├── deps.py                      # require_session、Origin 校验、分页参数
│       ├── errors.py                    # ApiError、异常处理器、requestId、fail_session 钩子
│       ├── pagination.py                # base64url 游标编解码
│       ├── schemas/                     # auth/project/provider/model/session/input/artifact/call
│       └── v1/
│           ├── router.py                # /api/v1 汇总与认证依赖挂载
│           ├── auth.py                  # 3 端点
│           ├── entrances.py             # 1 端点
│           ├── projects.py              # 4 端点
│           ├── providers.py             # 5 端点
│           ├── models.py                # 4 端点
│           ├── sessions.py              # 6 端点 + 文本输入
│           ├── artifacts.py             # 3 端点
│           └── calls.py                 # 3 端点（调用、列表、详情）
├── web/
│   ├── package.json                     # 前端依赖与脚本
│   ├── package-lock.json
│   ├── vite.config.ts                   # dev proxy → 后端；构建到 dist
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx                     # 挂载 App + QueryClient
│       ├── router.tsx                   # 8 条业务路由 + /login
│       ├── app/
│       │   ├── AppShell.tsx             # 侧边栏 248px / 顶栏 64px / 内容 1280px
│       │   ├── AuthGate.tsx             # 启动校验、401 跳转、next 白名单
│       │   └── Providers.tsx            # QueryClient、Toast
│       ├── lib/api/
│       │   ├── client.ts                # fetch 封装 credentials=same-origin
│       │   ├── errors.ts                # ApiError 类型与 code 分支
│       │   └── keys.ts                  # query keys
│       ├── styles/
│       │   ├── tokens.css               # interaction-design Design Tokens（不改名）
│       │   └── global.css               # 基础重置与排版
│       ├── components/ui/
│       │   ├── Button.tsx / IconButton.tsx
│       │   ├── Input.tsx                # Input / Textarea
│       │   ├── Select.tsx / Switch.tsx
│       │   ├── Badge.tsx                # Badge / StatusPill
│       │   ├── Loading.tsx              # Spinner / Skeleton
│       │   ├── Tooltip.tsx
│       │   ├── FormField.tsx
│       │   ├── ConfirmDialog.tsx        # Radix AlertDialog
│       │   └── Feedback.tsx             # EmptyState / ErrorState / Toast
│       ├── features/
│       │   ├── auth/                    # LoginPage / PasswordField / AuthBanner / hooks
│       │   ├── entrances/               # HomePage / EntranceGrid / EntranceCard / EntrancePage / PlaceholderPanel / RecentSessionTable
│       │   ├── projects/                # ProjectsPage / ProjectList / ProjectForm / ProjectDialog
│       │   ├── providers/               # ProvidersPage / ProviderTable / ProviderDialog / ProviderForm / SecretField / ConnectionTestBadge
│       │   ├── models/                  # ModelsPage / ModelTable / ModelDialog / ModelForm
│       │   ├── sessions/                # SessionsPage / SessionFilters / SessionTable / CreateSessionDialog / SessionDetailPage / SessionHeader / SessionTimeline / TimelineEvent / 四类事件卡
│       │   ├── composer/                # TextComposer / CharacterCounter / FileUploader / ArtifactCard
│       │   └── calls/                   # CallPanel / AdvancedParams / CallsPage / CallFilters / CallRecordTable / CallRecordRow
│       └── vite-env.d.ts
└── tests/
    ├── conftest.py                      # app/client/db/seeded fixtures、假 AI 适配器
    ├── test_config.py
    ├── test_entrances.py
    ├── test_crypto.py
    ├── test_password.py
    ├── test_redaction.py
    ├── test_engine.py
    ├── test_db_migrations.py
    ├── test_api_skeleton.py
    ├── test_storage.py
    ├── test_startup.py
    ├── test_sessions_service.py
    ├── test_artifacts_service.py
    ├── test_ai_gateway.py
    ├── test_ai_adapters.py
    ├── test_auth_service.py
    ├── test_auth_api.py
    ├── test_projects_service.py / test_projects_api.py
    ├── test_providers_service.py / test_providers_api.py
    ├── test_models.py
    ├── test_sessions_api.py
    ├── test_fail_session_hook.py
    ├── test_inputs_api.py
    ├── test_artifacts_api.py
    ├── test_calls_api.py
    ├── test_calls_query.py
    └── test_batch_b_smoke.py
```

## 文件职责说明

### 核心后端文件

| 文件路径 | 职责 | 主要导出 | 关联 |
|---------|------|---------|------|
| `src/workbench/config.py` | 环境变量声明与启动期校验 | `Settings`、`get_settings()` | AC-011-2、ADR-020 |
| `src/workbench/core/crypto.py` | 密钥加密与掩码 | `encrypt`、`decrypt`、`mask_secret` | AC-003-1、RISK-001 |
| `src/workbench/core/entrances.py` | 6 入口配置唯一来源 | `ENTRANCES`、`get_entrance(key)` | AC-001-1、AC-002-3 |
| `src/workbench/db/models/*` | 10 张表 ORM 定义 | 模型类 | AC-TECH-2 |
| `src/workbench/services/sessions.py` | 会话生命周期与事件（冻结签名） | `create`、`append_event`、`complete`、`fail_session`、`delete_session` | AC-009、AC-TECH-1 |
| `src/workbench/services/artifacts.py` | 制品落盘与事件（冻结签名） | `save` | AC-007、AC-TECH-1 |
| `src/workbench/services/ai_gateway.py` | 唯一模型出口（冻结签名） | `AiGateway.complete`、`AIResult`、`AIError` | AC-005、AC-TECH-1 |
| `src/workbench/adapters/fs/storage.py` | 路径隔离、原子写、trash、孤儿扫描 | `artifact_dir`、`safe_artifact_path`、`move_to_trash`、`scan_orphans` | AC-007、RISK-005 |
| `src/workbench/api/errors.py` | 统一错误体、requestId、未捕获异常标记失败 | `ApiError`、异常处理器 | AC-TECH-3、AC-009-4 |
| `src/workbench/main.py` | 应用装配与静态托管 | `create_app()` | ADR-008 / ADR-027 |

### API 路由文件

| 文件路径 | 方法 | 端点 | 关联 US |
|---------|------|------|---------|
| `api/v1/auth.py` | POST/GET | `/auth/login`、`/auth/logout`、`/auth/session` | US-011 |
| `api/v1/entrances.py` | GET | `/entrances` | US-001 / US-002 |
| `api/v1/projects.py` | GET/POST/PATCH | `/projects`、`/projects/{id}` | US-008 |
| `api/v1/providers.py` | GET/POST/PATCH | `/providers`、`/providers/{id}`、两个 connection-test | US-003 |
| `api/v1/models.py` | GET/POST/PATCH | `/models`、`/providers/{id}/models`、`/models/{id}` | US-004 |
| `api/v1/sessions.py` | GET/POST/PATCH/DELETE | `/sessions`、`/sessions/{id}`、`complete`、`events`、`inputs/text` | US-006 / US-009 |
| `api/v1/artifacts.py` | GET/POST | `/sessions/{id}/artifacts`、`/artifacts/{id}`、`/artifacts/{id}/content` | US-007 |
| `api/v1/calls.py` | GET/POST | `/sessions/{id}/calls`、`/calls`、`/calls/{id}` | US-005 / US-010 |

### 前端关键文件

| 文件路径 | 组件 | 关联 |
|---------|------|------|
| `web/src/app/AuthGate.tsx` | 登录态校验与原目标回跳 | AC-011-1 |
| `web/src/features/auth/LoginPage.tsx` | 登录页（default/submitting/error/locked/expired） | AC-011-2 ~ AC-011-6 |
| `web/src/features/entrances/HomePage.tsx` | 6 入口 + 最近 10 条会话 | AC-001-1 ~ AC-001-3 |
| `web/src/features/entrances/PlaceholderPanel.tsx` | planned 占位，无副作用 | AC-002-1 / AC-002-2 |
| `web/src/features/providers/ProviderForm.tsx` | 提供商表单、掩码密钥、连接测试 | AC-003-1 ~ AC-003-3 |
| `web/src/features/sessions/SessionTimeline.tsx` | 时间线与四类事件卡 | AC-009-3 / AC-005-4 |
| `web/src/features/composer/TextComposer.tsx` | 文本粘贴与 200,000 字符计数 | AC-006-1 ~ AC-006-3 |
| `web/src/features/composer/FileUploader.tsx` | 上传三查与同名提示 | AC-007-1 ~ AC-007-3 |
| `web/src/features/calls/CallPanel.tsx` | 发起调用与本次参数覆盖 | AC-005-1、AC-004-3 |
| `web/src/features/calls/CallsPage.tsx` | 调用记录筛选与展开核对 | AC-010-1 ~ AC-010-3 |

## 文件创建顺序

### 第一批（配置与基础，无依赖）
1. `pyproject.toml`、`uv.lock`、`.env.example`（TASK-TD-001）
2. `src/workbench/config.py`（TASK-TD-002）
3. `src/workbench/core/{constants,entrances,crypto,password,redaction}.py`（TASK-TD-003 ~ 006，可并行）
4. `.github/workflows/ci.yml`（TASK-TD-018，可与第二/三批并行）

### 第二批（数据层）
5. `src/workbench/db/base.py`、`db/engine.py`（TASK-TD-007）
6. `src/workbench/db/models/*.py`（10 个，TASK-TD-008）
7. `alembic.ini`、`migrations/env.py`、`migrations/versions/0001~0005`（TASK-TD-009）
8. `tests/test_db_migrations.py`（TASK-TD-010）

### 第三批（应用骨架与冻结契约）
9. `api/errors.py`、`api/deps.py`、`api/pagination.py`、`api/v1/router.py`、`main.py`（TASK-TD-011）
10. `adapters/fs/storage.py`（TASK-TD-012）
11. `services/errors.py`、`services/sessions.py`（TASK-TD-014）
12. `services/artifacts.py`（TASK-TD-015）
13. `adapters/ai/base.py`、`services/ai_gateway.py`（TASK-TD-016）
14. `adapters/ai/{openai_compatible,anthropic}.py`（TASK-TD-017）
15. `startup.py`（TASK-TD-013，可在 014 后）

### 第四批（认证与 CRUD）
16. `services/auth.py`、`db/repositories/auth.py` → `api/v1/auth.py`、`api/schemas/auth.py`（TASK-TD-019 / 020）
17. `services/projects.py` → `api/v1/projects.py`（TASK-TD-022 / 023）
18. `services/providers.py` → `api/v1/providers.py`（TASK-TD-025 / 026）
19. `services/models.py` → `api/v1/models.py`（TASK-TD-027）
20. `services/sessions.py` 状态流转 → `api/v1/sessions.py`（TASK-TD-030 / 031 / 032）
21. `api/v1/sessions.py` 文本输入、`api/v1/artifacts.py`（TASK-TD-035 / 036）
22. `api/v1/calls.py` 发起调用（TASK-TD-039）

### 第五批（前端）
23. `web/package.json`、`vite.config.ts`、`tsconfig.json`、`index.html`、`src/main.tsx`、`router.tsx`、`styles/tokens.css`、`app/*`（TASK-TD-021）
24. `components/ui/*` 原子与分子组件（TASK-TD-021）
25. `features/auth/*`（TASK-TD-021）
26. `features/projects/*`、`features/providers/*`、`features/models/*`（TASK-TD-024 / 028 / 029）
27. `features/sessions/*`、`features/composer/*`、`features/calls/*`（TASK-TD-033 / 034 / 037 / 038 / 040 / 043）
28. `features/entrances/*`（TASK-TD-044 / 045）

### 第六批（查询、部署与文档）
29. `services/calls.py`、`api/v1/calls.py` 查询端点（TASK-TD-042）
30. `startup.py` 归并用例补齐（TASK-TD-047）
31. `Dockerfile`、`docker-compose.yml`、`scripts/docker-entrypoint.sh`（TASK-TD-048）
32. `scripts/backup.sh`、`docs/dev-setup.md`、`README.md`（TASK-TD-049 / 050）

## 总文件数统计

| 类别 | 文件数 |
|------|--------|
| 配置文件 | 12（pyproject/uv.lock/alembic.ini/.env.example/.dockerignore/Dockerfile/compose/README/package.json/lock/vite/tsconfig） |
| 迁移 | 8（env、mako、5 个 revision） |
| 后端源码 | 约 45（core 5、db 19、services 8、adapters 4、api 约 20、main/config/startup 3） |
| 前端源码 | 约 55（app 3、lib 3、styles 2、ui 10、features 约 37） |
| 测试 | 30 |
| 脚本 | 2 |
| **合计** | **约 152** |

> 数量按模块估算，允许实现时合并同目录小文件；不得改变模块边界与文件名约定（`technical-design/change-spec.md` §2）。
