# Test Verification Design — workbench-core

> 阶段：test-verification。来源：`requirements-analysis/docs/context.md`（US-001 ~ US-011、AC 42 条）、`technical-design/tasks.md`（55 个任务、70 个 TC、TC ↔ AC 映射）、实现期补充 TC-071、`technical-design/docs/api-spec.md`、`technical-design/docs/database-schema.md`、`technical-design/design.md`（风险登记表）、`interaction-design/design.md`（31 项交互验证记录）。
> 依据：`approvals.md` 的 `tech-design · 2026-11-18 11:35:21 · 重新确认` 与 `tech-tasks · 2026-11-18 11:35:21 · 重新确认`（跨 spec 知识库注入扩展 ADR-042；55 任务 / 70 TC）。
> 既定口径（不改）：`aw.py verify` 只解析 pytest，pytest 是 71 个 TC 的权威结果来源；Vitest 复用同一 TC 编号作为 UI 第二实现，只进 CI `frontend-tests` job，不进 `.aw` 证据；本地 `aw verify` 只跑 SQLite，MySQL 由 CI job 2 覆盖；5 个 `[no-test]` 任务（TASK-TD-001/018/048/049/050）不映射 TC。
> 跨 spec TC 编号约定：core 使用 TC-001 ~ TC-071；knowledge-base 计划使用 TC-101 起；repo-integration 计划使用 TC-201 起。编号一经使用不复用、不交叉，避免多个 spec 的测试报告在 `aw verify` 解析时互相覆盖。
> 本体：`ontology-slices/test-verification.md` 不存在，不做本体对照。

## 测试策略

### 决策 1：测试框架选型

| 项 | 内容 |
|----|------|
| 选择 | 后端 pytest 8 + pytest-asyncio（`asyncio_mode=auto`）+ httpx `ASGITransport`；前端 Vitest + Testing Library（CI job 3，不产生 `.aw` 证据） |
| 理由 | 技术栈已由 tech-arch/tech-design 确认（Python 3.12 / FastAPI / SQLAlchemy async）；`ASGITransport` 直接驱动 ASGI 应用，不需要起 Uvicorn 与真实端口，CI 稳定；`aw.py verify` 的 pytest 预设（JUnit XML `aw.xml`）是既定权威来源 |
| 备选 | ① unittest + `TestClient`：异步事务与 `asyncio.timeout` 场景表达差；② Vitest 单独承担：无法覆盖 DB 迁移、加密、服务端并发；③ `.aw/packs` 约定的其他框架：仓库 `packs` 为空，无可用 pack |
| 权衡 | 不引入 pack（`alonwf pack add` 未执行）；假 AI 适配器与 `httpx.MockTransport` 只用在 HTTP 边界，服务层与 DB 保持真实，避免「mock 出来的绿」 |

### 决策 2：分层策略

- 单元层只覆盖纯函数与无 IO 组件（加解密、口令哈希、脱敏、常量、入口配置、路径解析）。
- 集成层用真实 SQLAlchemy + 临时 SQLite 文件库 + 真实 Alembic 迁移 + 真实 ASGI 路由，只在「AI 提供商 HTTP」与「文件系统故障」两个边界替身。
- 迁移层从空库 `alembic upgrade head`；MySQL 断言由 `AW_TEST_DATABASE_URL` 触发（CI job 2）。
- 契约层用显式签名/参数调用锁住四个冻结签名（`sessions.create` / `sessions.append_event` / `artifacts.save` / `AiGateway.complete`）。
- 人工层只放自动化无法可信模拟的项：视觉与双主题、真实浏览器 Cookie、compose 部署、备份恢复演练、TLS 反代。
- 禁止：把集成用例降级为 mock 服务层；把失败用例改为 skip；把 Vitest 结果写进 pytest 结论。

### 决策 3：数据库与隔离

- 每个用例独立 `tmp_path` 下的 SQLite 文件库，先 `alembic upgrade head` 再跑；不用共享内存库，避免迁移/WAL 与用例间污染。
- SQLite 配置与生产一致：`NullPool` + WAL + `busy_timeout=5000`；纯单元用例可用 `StaticPool` 内存库。
- 测试结束删除临时目录（含 `sessions/` 制品目录），不写仓库内 `data/`。
- MySQL 用例与 SQLite 是同一批用例：TC-059 在无 `AW_TEST_DATABASE_URL` 时必须仍能在 SQLite 上跑通（方言相关断言条件化），保证本地 `aw verify` 能看到 `test_tc059_*` 的结果；MySQL 独有断言只在 CI job 2 生效。

### 决策 4：时间、并发与外部边界

- 时间：服务层通过可注入的 `now()` 取当前时间；测试用固定时钟推进 8 小时空闲、5 分钟锁窗、游标排序，不 `sleep`。
- 并发：用 `asyncio.gather` 并发发起 5/6 次失败登录，断言计数与锁定；网关并发上限用信号量测试，不压真实上游。
- AI 边界：`adapters/ai/fake.py` 提供可控返回（成功文本、401/429/500、连接错误、超时、延迟）；协议适配器用 `httpx.MockTransport` 校验请求构造。
- 文件系统故障：monkeypatch 存储适配器的写入/移动抛 `OSError`，覆盖 507 与清理路径，不修改磁盘权限。

### 决策 5：跨 spec 的 TC 编号与证据边界

- core 使用 **TC-001 ~ TC-071**（TC-001 ~ TC-063 为基线，TC-064 ~ TC-070 为 2026-11-18 知识库注入扩展，TC-071 为 DB 错误映射方言回归）；knowledge-base spec 计划使用 **TC-101 起**；repo-integration spec 计划使用 **TC-201 起**。
- 编号段一经分配不复用、不改号；各 spec 的 pytest 用例名都带本段编号，避免 `aw.py verify` 在一个仓库内解析多个 spec 的报告时把同名 TC 归并成一条。
- 跨 spec 契约（`InjectionPreparer`、`knowledge_base` 表、`kbDeleted`）在 core 侧只由假实现与读时左连接验证；知识库导入/检索/失效判定/正文组装的 TC 属 knowledge-base spec（TC-101 起），core 不重复造用例。
- 前端 Vitest 仍复用各自 spec 的同一编号作为第二实现，不产生新编号。

## 测试分层

| 层次 | 覆盖范围 | 工具 | 对应用例 | 占比（估算） |
|------|---------|------|---------|-------------|
| 单元 | crypto、password、redaction、config、constants/entrances、storage 路径解析 | pytest | TC-002、TC-009、TC-017、TC-039、TC-040、TC-051、TC-056、TC-057（settings）、TC-063 | 约 15% |
| 集成·服务 | 项目、提供商、模型、会话、事件、制品、网关、注入留痕、启动自检 | pytest + 临时 SQLite 文件库 | TC-001、TC-003 ~ TC-008、TC-013 ~ TC-016、TC-018 ~ TC-022、TC-025 ~ TC-030、TC-036、TC-038、TC-041 ~ TC-045、TC-049、TC-050、TC-053、TC-065 ~ TC-067 | 约 45% |
| 集成·接口 | 30 个端点、错误体、鉴权、Origin、上传、调用查询、`/ai/complete` 注入 | pytest + httpx `ASGITransport` | TC-001、TC-008、TC-010 ~ TC-012、TC-013 ~ TC-016、TC-017 ~ TC-024、TC-026 ~ TC-037、TC-039 ~ TC-048、TC-051 ~ TC-056、TC-060、TC-061、TC-065 ~ TC-070 | 约 30% |
| 迁移/方言 | 空库到 head（0001 ~ 0006）、10 张表约束、MySQL 复跑 | alembic + pytest（SQLite / CI MySQL） | TC-058、TC-059、TC-064 | 约 5% |
| 冒烟 | 批次 B 最小闭环 | pytest + 假适配器 | TC-062 | 约 2% |
| UI 第二实现 | 同一 TC 编号的组件行为 | Vitest + Testing Library（CI job 3，不进证据） | TC-001、TC-008、TC-010、TC-013、TC-014、TC-016、TC-017、TC-018、TC-021、TC-023、TC-024、TC-025、TC-026、TC-027、TC-028、TC-029、TC-030、TC-031、TC-032、TC-033、TC-034、TC-036、TC-038、TC-041、TC-044、TC-046、TC-047、TC-048、TC-051、TC-054、TC-070 | 不计入 TC 结果 |
| 人工验收 | 视觉/双主题、真实浏览器 Cookie、部署、备份恢复、TLS 反代、长调用体验 | 浏览器 / docker compose / mysqldump | M-01 ~ M-06（见 §人工验证清单） | 不计入 TC 结果 |

## 测试数据与环境策略

### 环境变量（测试固定值，不含真实密钥）

| 变量 | 测试值 | 用途 |
|------|--------|------|
| `AW_ADMIN_PASSWORD` | `test-admin-pass-001` | 登录用例；缺失场景由 TC-009 单独构造 |
| `AW_ENCRYPTION_KEY` | 32 字节 base64 常量（测试专用） | 提供商密钥加解密 |
| `AW_DATA_DIR` | `tmp_path/data` | 制品目录 |
| `AW_DATABASE_URL` | `sqlite+aiosqlite:///{tmp_path}/test.db` | 集成用例数据库 |
| `AW_PUBLIC_ORIGIN` | `http://testserver` | Origin 校验；测试客户端默认带 `Origin: http://testserver` |
| `AW_COOKIE_SECURE` | `auto`（TC-008 分别覆盖 `true`/`false`） | Cookie 属性 |
| `AW_TEST_DATABASE_URL` | 仅 CI job 2 设置 | MySQL 方言复跑 |
| `AW_PROMPT_MAX_CHARS` | 默认 200000 | 文本/提示上限 |
| `AW_AI_MAX_CONCURRENCY` | 默认 4；TC-045 可改为 1 | 网关并发 |

### 夹具（`tests/conftest.py` 扩展）

| 夹具 | 行为 |
|------|------|
| `settings` | 用测试环境变量构造 `Settings`，覆盖默认值 |
| `db_path` | `tmp_path/test.db`，用例级独立 |
| `app` | `create_app()`，注入假 AI 适配器与固定时钟 |
| `client` | `httpx.AsyncClient(transport=ASGITransport(app), base_url="http://testserver")`，默认带同源 `Origin` |
| `logged_in_client` | 先 `POST /api/v1/auth/login` 获得 `aw_session` Cookie |
| `project` / `provider` / `model` / `session` | 通过服务或 API 创建的前置数据 |
| `fake_ai` | 可编程假适配器（成功/401/429/500/连接错误/超时/延迟） |
| `clock` | 可推进的固定时钟，供 8h/5min/排序使用 |
| `upload_file` | 生成指定扩展名/字节数的临时文件（含 10MB、10MB+1） |

### 测试数据矩阵

| 类别 | 取值 | 用途 |
|------|------|------|
| 文本边界 | 1 字符、200000 字符、200001 字符、纯空白 `" \n\t "`、含 Unicode 与 emoji | TC-032 ~ TC-035 |
| 上传类型 | `.txt .md .markdown .log .json .yaml .yml .csv .sql` 合法；`.exe .pdf .html .LOG.exe` 非法 | TC-036 ~ TC-039 |
| 上传大小/数量 | 0 字节、1 字节、恰好 10MB、10MB+1、9 个、10 个、11 个 | TC-037、TC-040 |
| 文件名 | 中文名、超长名、`../../etc/passwd`、`..%2F`、`..\\x`、同名重复 1/2/3 次 | TC-038、TC-039 |
| 项目/模型名 | 1 字符、100 字符（项目）、191 字符（模型）、大小写不同、前后空格 | TC-013、TC-016、TC-024 |
| 参数 | temperature 0 / 2 / -0.01 / 2.01；max_tokens 1 / 1000000 / 0 | TC-023、TC-025 |
| 登录 | 正确口令、错误口令、空口令、5 次连续失败、不同 IP、锁定期内正确口令 | TC-002 ~ TC-005 |
| 时间 | 7h59m、恰好 8h、8h+1s；锁 4m59s、5m、5m+1s | TC-004、TC-006 |
| 凭据 | 合法密文、篡改密文、错误密钥、`v2:` 前缀、非 base64 | TC-017、TC-050 |
| 提示/摘要 | 1 字符、200000 字符、含 `sk-` 与 `Authorization` 的文本 | TC-041、TC-044、TC-063 |
| 注入快照 | `injection=None`；单条/多条 `InjectionItem`；`injected_chars` 与 `sum(items)` 不符；`total_chars` 与 `len(prepared)` 不符；`entryCodes` 空/重复；`excludedCodes` 非空；预算 199999/200000/200001 | TC-064 ~ TC-070 |
| `kbDeleted` | `knowledge_base` 表存在且行在（false）、行已删（true）、表不存在（true） | TC-067、TC-070 |
| 失效确认 | 失效集为空、未确认、部分确认、精确匹配、确认后有效集为空 | TC-068、TC-069 |

### 数据卫生

- 不提交任何真实密钥、真实提供商响应、真实用户数据；日志断言只检查「不含原文」。
- 生成的大文件（10MB）只写 `tmp_path`，用例结束自动清理。
- 测试不使用外网；所有 AI 请求被假适配器或 `MockTransport` 拦截。

## 测试用例列表

### TC-001：未登录访问受保护资源被拦截
- 测试目的：验证除登录页/登录接口外的页面与接口都要求登录，且 401 不泄露业务字段。
- 测试类型：集成·接口（pytest）；Vitest 第二实现（AuthGate）
- 关联需求：AC-011-1；任务 TASK-TD-019 / 020 / 021
- 涉及本体：无
- 自动化落点：`tests/test_auth_service.py::test_tc001_unauthorized_without_session`；`tests/test_auth_api.py::test_tc001_api_401_and_html_redirect`
- 前置条件：应用已启动，未携带 `aw_session` Cookie。
- 测试步骤：
  1. 无 Cookie 请求 `GET /api/v1/sessions`，并逐一抽查 `/projects`、`/providers`、`/calls`。
  2. 无 Cookie 以 `Accept: text/html` 请求 `/sessions`。
  3. 检查响应体与响应头。
- 预期结果：
  1. 全部 401，错误体只有 `code=unauthorized`、`message`、`details`、`requestId`，无项目/会话/调用字段。
  2. HTML 导航 302 到 `/login?next=%2Fsessions`。
  3. 响应无 `Set-Cookie`，无业务数据。
- 边界异常数据：伪造随机 token、空 Cookie、`aw_session=`（空值）。

### TC-002：正确口令登录并只存令牌哈希
- 测试目的：验证正确口令登录成功、响应不含口令或哈希、库中只存令牌哈希。
- 测试类型：单元（口令）+ 集成·服务
- 关联需求：AC-011-2；任务 TASK-TD-005 / 019 / 020
- 涉及本体：无
- 自动化落点：`tests/test_password.py::test_tc002_password_verify_contract`；`tests/test_auth_service.py::test_tc002_login_issues_token_hash_only`
- 前置条件：`admin_credential` 已由启动自检写入口令哈希。
- 测试步骤：
  1. 调用 `verify_password` 校验正确/错误口令与非法编码串。
  2. `POST /api/v1/auth/login` 提交正确口令。
  3. 查询 `login_session` 行与响应体。
- 预期结果：
  1. 正确口令 True，错误口令 False，非法编码串 False 不抛异常。
  2. 200 `{"authenticated":true}` 并下发 `aw_session`；响应无口令、哈希、令牌原文以外的敏感字段。
  3. 库中只有 SHA-256 哈希（与原文不同），无明文令牌。
- 边界异常数据：1 字符口令、含 Unicode 口令、口令前后空格（按原样比较）。

### TC-003：错误口令统一提示且日志无原文
- 测试目的：验证错误口令返回不区分原因的统一提示，不签发令牌，日志与响应不含口令。
- 测试类型：集成·接口
- 关联需求：AC-011-3；任务 TASK-TD-019
- 涉及本体：无
- 自动化落点：`tests/test_auth_service.py::test_tc003_wrong_password_uniform_error`
- 前置条件：已配置管理员口令。
- 测试步骤：
  1. `POST /auth/login` 提交错误口令，捕获响应与 caplog。
  2. 再提交另一个错误口令。
- 预期结果：
  1. 两次都 401 `login_failed`，`message` 完全一致（「口令错误，请重试。」），无 `Set-Cookie`。
  2. 响应与日志中不出现提交的口令原文或哈希。
- 边界异常数据：空口令（400，`code` 字段表示校验失败）、仅空白口令、超长口令（不触发 500）。

### TC-004：连续失败 5 次锁定 5 分钟、成功清零
- 测试目的：验证同来源 IP 连续失败 5 次后锁定 5 分钟，锁定期不校验口令，成功登录后计数清零。
- 测试类型：集成·服务（时钟注入）
- 关联需求：AC-011-4；任务 TASK-TD-019
- 涉及本体：无
- 自动化落点：`tests/test_auth_service.py::test_tc004_lock_after_five_failures`
- 前置条件：固定时钟；同一来源 IP。
- 测试步骤：
  1. 连续 4 次错误口令，第 5 次错误口令，第 6 次尝试（含正确口令）。
  2. 推进时钟 4m59s、5m、5m+1s 分别重试。
  3. 锁定窗口外成功登录，再检查计数。
- 预期结果：
  1. 第 5 次后写 `locked_until`；第 6 次返回 429 `login_locked` + `Retry-After`，锁定期内正确口令也不放行。
  2. 4m59s 仍 429；5m 时允许重新校验；成功登录删除 `login_attempt` 行。
  3. 已建立的其他登录会话不受影响。
- 边界异常数据：不同 IP 不共享计数；失败窗口跨越 5 分钟边界时计数重置。

### TC-005：并发失败计数不丢
- 测试目的：验证同一 IP 并发失败请求下计数准确，不因竞态少计。
- 测试类型：集成·服务（并发）
- 关联需求：AC-011-4；任务 TASK-TD-019
- 涉及本体：无
- 自动化落点：`tests/test_auth_service.py::test_tc005_concurrent_failures_counted`
- 前置条件：SQLite 文件库（WAL）；同一 IP。
- 测试步骤：
  1. 用 `asyncio.gather` 并发发起 6 次错误口令登录。
  2. 查询 `login_attempt` 与 `login_session`。
- 预期结果：
  1. 计数为 5 或 6 且不丢失（≥5），至少一次返回 429。
  2. 无成功令牌签发，库中无明文口令。
- 边界异常数据：5 次与 6 次并发；SQLite 写锁下不得出现 `database is locked` 泄漏到响应（RISK-004）。

### TC-006：空闲 8 小时失效、每次请求刷新 lastSeenAt、无绝对上限
- 测试目的：验证空闲 8 小时过期语义与活跃续期。
- 测试类型：集成·服务（时钟注入）
- 关联需求：AC-011-5；任务 TASK-TD-019
- 涉及本体：无
- 自动化落点：`tests/test_auth_service.py::test_tc006_idle_expiry_and_refresh`
- 前置条件：已登录。
- 测试步骤：
  1. 推进 7h59m 后请求一次，记录 `last_seen_at`。
  2. 再推进 7h59m（累计活跃超过 8h）后请求。
  3. 从最后一次请求推进 8h+1s 后请求。
- 预期结果：
  1. 请求成功且 `last_seen_at` 刷新。
  2. 累计时长超过 8h 仍有效（无绝对上限）。
  3. 返回 401 `unauthorized`。
- 边界异常数据：恰好 8h；8h 前后 1 秒；并发请求刷新。

### TC-007：登出立即吊销令牌
- 测试目的：验证登出写 `revoked_at`，旧令牌后续请求 401，Cookie 被清除。
- 测试类型：集成·接口
- 关联需求：AC-011-6；任务 TASK-TD-019 / 020
- 涉及本体：无
- 自动化落点：`tests/test_auth_service.py::test_tc007_logout_revokes_token`；`tests/test_auth_api.py::test_tc007_api_logout_clears_cookie`（可用 TC-007 同名后缀）
- 前置条件：已登录。
- 测试步骤：
  1. `POST /auth/logout`。
  2. 用原 Cookie 请求受保护接口。
  3. 再次登出。
- 预期结果：
  1. 204 无体，`Set-Cookie: aw_session=; Max-Age=0`。
  2. 原令牌 401；库中 `revoked_at` 非空。
  3. 第二次登出 401（前端按已登出处理）。
- 边界异常数据：被吊销令牌与新建令牌并存；登出后重启不复活。

### TC-008：Cookie 属性 HttpOnly / SameSite=Lax / Secure 条件生效
- 测试目的：验证登录 Cookie 的安全属性与令牌不出现在 URL/前端可读存储。
- 测试类型：集成·接口
- 关联需求：AC-011-7；任务 TASK-TD-020 / 021
- 涉及本体：无
- 自动化落点：`tests/test_auth_api.py::test_tc008_cookie_attributes`
- 前置条件：可切换 `AW_COOKIE_SECURE`。
- 测试步骤：
  1. `AW_COOKIE_SECURE=false` 登录，检查 `Set-Cookie`。
  2. 改为 `true` 登录，检查 `Set-Cookie`。
  3. 检查响应体与前端构建产物是否含令牌。
- 预期结果：
  1. 含 `HttpOnly`、`SameSite=Lax`、`Path=/`，不含 `Secure`。
  2. 含 `Secure`。
  3. 令牌不在 URL、响应 JSON、localStorage/sessionStorage 代码路径中。
- 边界异常数据：`auto` + http 不含 Secure；`auto` + https 含 Secure。

### TC-009：`AW_ADMIN_PASSWORD` 缺失或空拒绝启动
- 测试目的：验证启动期环境校验 fail-fast。
- 测试类型：单元（config）
- 关联需求：AC-011-2、AC-TECH-1；任务 TASK-TD-002
- 涉及本体：无
- 自动化落点：`tests/test_config.py::test_tc009_missing_admin_password_refuses_start`
- 前置条件：构造不含 `AW_ADMIN_PASSWORD` 的环境。
- 测试步骤：
  1. 构造 `Settings`（缺失变量）。
  2. 构造空串与纯空白值。
  3. 构造合法值。
- 预期结果：
  1. 抛可读校验错误（指明变量名），错误信息不含密钥值。
  2. 空串/空白同样拒绝。
  3. 合法值通过并给出 `AW_PROMPT_MAX_CHARS=200000` 等默认值。
- 边界异常数据：`AW_ENCRYPTION_KEY` 非 32 字节、非法 base64、`AW_COOKIE_SECURE=maybe`。

### TC-010：HTML 导航 302 并保留站内 next
- 测试目的：验证未登录页面导航跳转登录页并携带原目标。
- 测试类型：集成·接口
- 关联需求：AC-011-1；任务 TASK-TD-020 / 021
- 涉及本体：无
- 自动化落点：`tests/test_auth_api.py::test_tc010_login_next_is_internal_only`
- 前置条件：未登录。
- 测试步骤：
  1. 请求 `/sessions/42?tab=timeline`（HTML）。
  2. 登录后检查跳转目标。
  3. 直接访问 `/login` 不带 next。
- 预期结果：
  1. 302 `/login?next=%2Fsessions%2F42%3Ftab%3Dtimeline`。
  2. 登录后回到原路径与查询串。
  3. 登录后进入 `/`。
- 边界异常数据：next 含中文/特殊字符（正确编码）；next 为绝对 URL（见 TC-012）。

### TC-011：空闲过期后 API 401 与页面跳转
- 测试目的：验证过期会话的接口与页面行为一致。
- 测试类型：集成·接口（时钟注入）
- 关联需求：AC-011-5；任务 TASK-TD-020
- 涉及本体：无
- 自动化落点：`tests/test_auth_api.py::test_tc011_expired_session_redirects`
- 前置条件：已登录，时钟可推进。
- 测试步骤：
  1. 推进 8h+1s 后请求 `GET /api/v1/auth/session`。
  2. 以 HTML 请求 `/sessions`。
- 预期结果：
  1. 401 `unauthorized`，无业务字段。
  2. 302 `/login?next=%2Fsessions`。
- 边界异常数据：过期前后 1 秒；过期令牌与有效令牌并存。

### TC-012：next 只接受站内路径
- 测试目的：验证开放重定向防护。
- 测试类型：集成·接口
- 关联需求：AC-011-1；任务 TASK-TD-020
- 涉及本体：无
- 自动化落点：`tests/test_auth_api.py::test_tc012_next_rejects_external_url`
- 前置条件：未登录。
- 测试步骤：
  1. 分别请求 `?next=https://evil.example`、`//evil.example`、`/\evil.example`、`javascript:alert(1)`。
  2. 登录后检查最终跳转。
- 预期结果：
  1. 全部回退到 `/`，不跳外部域。
  2. 合法站内路径 `/providers` 正常保留。
- 边界异常数据：`%2F%2Fevil`、含 CRLF 的 next、空 next。

### TC-013：创建项目与重名 409（大小写不敏感）
- 测试目的：验证项目创建返回 projectId、名称唯一。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-008-1；任务 TASK-TD-022 / 023 / 024
- 涉及本体：无
- 自动化落点：`tests/test_projects_service.py::test_tc013_create_project_and_duplicate`；`tests/test_projects_api.py::test_tc013_api_create_and_conflict`
- 前置条件：已登录。
- 测试步骤：
  1. 创建项目「支付中心」，再创建「 支付中心 」「支付中心」大小写变体。
  2. 检查库中 `name_key`。
- 预期结果：
  1. 首次 201 返回 `projectId`；重名 409 `project_name_duplicate`，`details[].field=name`。
  2. `name_key` 为 `casefold()` 归一值。
- 边界异常数据：全角/半角、Unicode 大小写、前后空格。

### TC-014：编辑项目回显与 updatedAt 刷新
- 测试目的：验证 PATCH 部分更新、显式 null 清空、最后更新时间。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-008-2；任务 TASK-TD-022 / 023 / 024
- 涉及本体：无
- 自动化落点：`tests/test_projects_service.py::test_tc014_update_reflects_and_touches`；`tests/test_projects_api.py::test_tc014_api_patch`
- 前置条件：已创建项目。
- 测试步骤：
  1. PATCH 修改 `techStack`，GET 详情。
  2. PATCH 显式 `notes: null`。
  3. 比较 `updatedAt`。
- 预期结果：
  1. 返回与再查询都显示最新值。
  2. `notes` 被清空。
  3. `updatedAt` 严格增大。
- 边界异常数据：空对象 PATCH、未知字段、404 项目。

### TC-015：无项目不可创建会话
- 测试目的：验证创建会话必须有存在的项目。
- 测试类型：集成·接口
- 关联需求：AC-008-3；任务 TASK-TD-023
- 涉及本体：无
- 自动化落点：`tests/test_projects_api.py::test_tc015_session_requires_project`
- 前置条件：已登录；无对应项目。
- 测试步骤：
  1. `POST /api/v1/sessions` 传不存在的 `projectId`。
  2. 检查 `analysis_session` 行数。
- 预期结果：
  1. 404 `project_not_found`，`details` 指明字段。
  2. 不写任何会话行。
- 边界异常数据：`projectId=0`、负数、字符串、null。

### TC-016：项目名称与仓库地址逐字段校验
- 测试目的：验证 400 逐字段错误且不写库。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-008-1；任务 TASK-TD-022 / 023 / 024
- 涉及本体：无
- 自动化落点：`tests/test_projects_service.py::test_tc016_name_validation`；`tests/test_projects_api.py::test_tc016_api_validation_fields`
- 前置条件：已登录。
- 测试步骤：
  1. 提交空名、纯空白名、101 字符名。
  2. 提交 `repoUrl`：`ftp://x`、`http://user:pass@host`、超过 500 字符。
  3. 检查库。
- 预期结果：
  1. 400，`details[].field` 分别为 `name`、`repoUrl`。
  2. 无项目行写入。
  3. 100 字符名与合法 `https://` 地址通过。
- 边界异常数据：1/100/101 字符；`javascript:` 伪协议；带查询串的合法 URL。

### TC-017：密钥加密落库、掩码展示、响应无密钥
- 测试目的：验证 AES-256-GCM 往返与篡改检测、API 只返回掩码。
- 测试类型：单元（crypto）+ 集成·服务/接口
- 关联需求：AC-003-1；任务 TASK-TD-004 / 025 / 026 / 028
- 涉及本体：无
- 自动化落点：`tests/test_crypto.py::test_tc017_crypto_roundtrip_and_tamper`；`tests/test_providers_service.py::test_tc017_provider_key_encrypted_and_masked`；`tests/test_providers_api.py::test_tc017_api_never_returns_secret`
- 前置条件：已登录；合法 `AW_ENCRYPTION_KEY`。
- 测试步骤：
  1. `encrypt` → `decrypt` 往返；篡改密文、改版本前缀、非 base64、错误密钥。
  2. 创建提供商，查询库中 `api_key_ciphertext` 与响应。
  3. GET 列表与详情。
- 预期结果：
  1. 往返一致；篡改/格式错误抛 `CredentialUnavailable`，异常文本不含密文。
  2. 库中为 `v1:<nonce>:<ciphertext>`，响应只有 `apiKeyMasked`（形如 `sk-****1234`）。
  3. 所有响应不含 `apiKey` 或密文。
- 边界异常数据：1 字符密钥、512 字符密钥、含 Unicode 的密钥、空字符串（按未提供处理）。

### TC-018：提供商必填与 baseURL 校验
- 测试目的：验证非法输入拒绝且不写库。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-003-2；任务 TASK-TD-025 / 026 / 028
- 涉及本体：无
- 自动化落点：`tests/test_providers_service.py::test_tc018_provider_validation`；`tests/test_providers_api.py::test_tc018_api_validation`
- 前置条件：已登录。
- 测试步骤：
  1. 缺 `name`/`protocol`/`baseUrl`/`apiKey` 分别提交。
  2. 提交非法协议、`ftp://`、带 userinfo 的 URL、>500 字符 URL。
- 预期结果：
  1. 400，逐字段 `details[].field`。
  2. 无 `provider_config` 行写入；合法值 201。
- 边界异常数据：`openai-compatible`（连字符）应被拒，仅接受 `openai_compatible`；`baseUrl` 末尾斜杠归一。

### TC-019：连接测试 10s 超时且无副作用
- 测试目的：验证连接测试独立 10s 超时、不写会话/制品/调用记录。
- 测试类型：集成·服务（假适配器）
- 关联需求：AC-003-3；任务 TASK-TD-017 / 025 / 026
- 涉及本体：无
- 自动化落点：`tests/test_ai_adapters.py::test_tc019_connection_test_timeout`；`tests/test_providers_service.py::test_tc019_connection_test_timeout`；`tests/test_providers_api.py::test_tc019_api_connection_test`
- 前置条件：已保存提供商；假适配器可配置延迟。
- 测试步骤：
  1. 假适配器延迟 10.1s 触发连接测试。
  2. 记录四张表的行数（session/event/artifact/ai_call_record）。
- 预期结果：
  1. 200 `{"ok":false,"errorCode":"timeout","latencyMs":…}`（上游失败仍 200）。
  2. 行数不变；不产生制品文件。
- 边界异常数据：9.9s 成功、10s 边界、连接失败（unreachable）。

### TC-020：停用提供商后模型不可选、历史可查
- 测试目的：验证停用只改 `enabled`，影响可选列表但不删历史。
- 测试类型：集成·服务
- 关联需求：AC-003-4；任务 TASK-TD-025
- 涉及本体：无
- 自动化落点：`tests/test_providers_service.py::test_tc020_disabled_provider_blocks_models`
- 前置条件：提供商启用且有模型与历史调用记录。
- 测试步骤：
  1. PATCH 停用提供商。
  2. `GET /models?enabled=true`。
  3. 查询历史 `ai_call_record` 与 `model_binding`。
- 预期结果：
  1. 其模型不出现在可选列表。
  2. 历史调用记录仍可查询（模型/提供商快照完整）。
  3. `model_binding` 行未被级联修改。
- 边界异常数据：重新启用后模型恢复可选；停用后创建会话/调用返回 409 `provider_disabled`。

### TC-021：连接测试失败分类
- 测试目的：验证上游错误映射为固定 `errorCode`。
- 测试类型：集成·服务（假适配器 / MockTransport）
- 关联需求：AC-003-3；任务 TASK-TD-017 / 025 / 026 / 028
- 涉及本体：无
- 自动化落点：`tests/test_ai_adapters.py::test_tc021_connection_test_error_classification`；`tests/test_providers_service.py::test_tc021_connection_test_error_codes`；`tests/test_providers_api.py::test_tc021_api_connection_test_failure`
- 前置条件：已保存提供商。
- 测试步骤：
  1. 依次模拟 401、429、500、连接拒绝、400。
  2. 解密失败提供商（密文损坏）执行连接测试。
- 预期结果：
  1. `errorCode` 分别为 `auth`、`rate_limit`、`server_error`、`unreachable`、`invalid_request`。
  2. 解密失败为 `credential_unavailable`；响应与错误文本无密钥。
- 边界异常数据：403、502、超时与网络错误并发。

### TC-022：空密钥不改、新值重新加密
- 测试目的：验证 PATCH 省略/空 `apiKey` 不修改密文，新值重新加密。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-003-1；任务 TASK-TD-025 / 026
- 涉及本体：无
- 自动化落点：`tests/test_providers_service.py::test_tc022_update_key_blank_keeps`；`tests/test_providers_api.py::test_tc022_api_patch_key`
- 前置条件：已保存提供商。
- 测试步骤：
  1. PATCH 不传 `apiKey`，再传 `""`，比较密文。
  2. PATCH 传新密钥，比较密文与掩码。
- 预期结果：
  1. 密文逐字节不变。
  2. 新密文不同（随机 nonce），掩码后四位更新，解密得新密钥。
- 边界异常数据：仅空白字符串（`"  "`）按非法密钥拒绝或按新值处理，需与实现一致并在此用例固定。

### TC-023：新增模型与参数范围
- 测试目的：验证模型登记与 temperature/max_tokens 边界。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-004-1；任务 TASK-TD-027 / 029
- 涉及本体：无
- 自动化落点：`tests/test_models.py::test_tc023_create_model_and_ranges`
- 前置条件：启用中的提供商。
- 测试步骤：
  1. 新增模型并查询 `GET /models?enabled=true`。
  2. 提交 temperature `-0.01`、`2.01`、`0`、`2`。
  3. 提交 `defaultMaxTokens` 0、1、1000000、1000001。
- 预期结果：
  1. 新模型出现在可选列表。
  2. 越界 400（校验失败）；0/2 通过。
  3. 0 与 1000001 拒绝；1 与 1000000 通过。
- 边界异常数据：两位小数 `0.25`、三位小数 `0.255`（按两位小数规则判定）、负数。

### TC-024：同提供商同名模型 409
- 测试目的：验证模型名在同一提供商内唯一（大小写不敏感）。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-004-2；任务 TASK-TD-027 / 029
- 涉及本体：无
- 自动化落点：`tests/test_models.py::test_tc024_duplicate_model_name`
- 前置条件：提供商下已有 `gpt-4.1`。
- 测试步骤：
  1. 再建 `GPT-4.1` 与 ` gpt-4.1 `。
  2. 在另一提供商下建 `gpt-4.1`。
- 预期结果：
  1. 409 `model_name_duplicate`，`details[].field=modelName`。
  2. 另一提供商允许同名。
- 边界异常数据：Unicode 大小写、全角字符。

### TC-025：默认参数生效、本次覆盖不回写
- 测试目的：验证调用使用模型默认参数，显式覆盖只作用于本次。
- 测试类型：集成·服务（假适配器捕获参数）
- 关联需求：AC-004-3；任务 TASK-TD-027 / 040
- 涉及本体：无
- 自动化落点：`tests/test_models.py::test_tc025_default_params_used_and_override_not_persisted`
- 前置条件：模型默认 temperature 0.7 / max_tokens 1024。
- 测试步骤：
  1. 不传覆盖参数调用一次。
  2. 传 `temperature=0.2, maxTokens=2048` 调用一次。
  3. 重新查询模型。
- 预期结果：
  1. 假适配器收到 0.7 / 1024。
  2. 收到 0.2 / 2048。
  3. 模型默认值仍为 0.7 / 1024。
- 边界异常数据：覆盖 temperature=0、maxTokens=1；覆盖值越界 400。

### TC-026：创建会话、状态进行中、置顶
- 测试目的：验证会话创建契约与列表置顶。
- 测试类型：契约 + 集成·服务 + 接口
- 关联需求：AC-009-1；任务 TASK-TD-014 / 030 / 031 / 033
- 涉及本体：无
- 自动化落点：`tests/test_sessions_service.py::test_tc026_create_session_contract`；`tests/test_sessions_service.py::test_tc026_create_session`；`tests/test_sessions_api.py::test_tc026_api_create_session`
- 前置条件：项目 + 启用模型。
- 测试步骤：
  1. 以关键字参数调用 `sessions.create(project_id=…, entrance_key=…, title=…, model_id=…)`。
  2. `POST /api/v1/sessions` 创建。
  3. 查询项目会话列表。
- 预期结果：
  1. 返回 `SessionView`，字段与冻结签名一致。
  2. 201，`status=in_progress`，生成 `sessionId`。
  3. 新会话按 `updated_at` 倒序置顶。
- 边界异常数据：标题 1/200/201 字符；非法 `entranceKey`；停用模型 409；不存在项目 404。

### TC-027：项目/状态筛选与倒序、游标分页
- 测试目的：验证列表筛选、排序与分页稳定性。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-009-2；任务 TASK-TD-030 / 031 / 033
- 涉及本体：无
- 自动化落点：`tests/test_sessions_service.py::test_tc027_list_filters`；`tests/test_sessions_api.py::test_tc027_api_filters`
- 前置条件：两个项目、多状态会话。
- 测试步骤：
  1. 按 `projectId`、`status` 分别筛选。
  2. 按 `limit=2` 翻页两次。
- 预期结果：
  1. 只返回匹配项，`updated_at DESC, session_id DESC`。
  2. 两页无重复无遗漏，`nextCursor` 正确。
- 边界异常数据：无匹配返回空 `items`；`limit=0/101` 400；非法 status 400。

### TC-028：时间线按发生顺序
- 测试目的：验证事件时间线升序与分页。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-009-3；任务 TASK-TD-030 / 031 / 034
- 涉及本体：无
- 自动化落点：`tests/test_sessions_service.py::test_tc028_timeline_order`；`tests/test_sessions_api.py::test_tc028_api_events_order`
- 前置条件：会话含 input_text、call、artifact、status_change 事件。
- 测试步骤：
  1. 写入四类事件后请求 `GET /sessions/{id}/events`。
  2. 用 `limit=2` 翻页。
- 预期结果：
  1. `event_id ASC`，顺序与写入一致，payload 完整。
  2. 翻页不重不漏；默认 limit 50、上限 200。
- 边界异常数据：201 条事件分页；无事件返回空列表。

### TC-029：完成/失败终态拒绝写入
- 测试目的：验证状态流转与终态只读。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-009-4；任务 TASK-TD-030 / 031 / 032 / 033
- 涉及本体：无
- 自动化落点：`tests/test_sessions_service.py::test_tc029_terminal_state_rejects`；`tests/test_sessions_api.py::test_tc029_api_complete_idempotent`；`tests/test_fail_session_hook.py::test_tc029_unhandled_error_marks_failed`
- 前置条件：进行中会话。
- 测试步骤：
  1. `POST /complete`，再提交文本、上传、调用；重复 `POST /complete`。
  2. 触发未捕获异常端点，检查状态与事件。
- 预期结果：
  1. 完成写 `status_change(local-user)` 与 `closed_at`；后续写入 409 `session_closed`；重复完成 409。
  2. 未捕获异常把会话标记 `failed`，事件 `actor=system`；业务错误 400/404/409/502/504 不改状态。
- 边界异常数据：已完成会话标记失败；失败会话再完成；无会话上下文的异常不改任何状态。

### TC-030：删除会话级联清理且不影响其他会话
- 测试目的：验证事件、制品文件与调用记录一并删除。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-009-5；任务 TASK-TD-030 / 031 / 046
- 涉及本体：无
- 自动化落点：`tests/test_sessions_service.py::test_tc030_delete_cascades`；`tests/test_sessions_api.py::test_tc030_api_delete`
- 前置条件：目标会话有事件、2 个制品文件、调用记录；另有其他会话。
- 测试步骤：
  1. `DELETE /sessions/{id}`。
  2. 查询四类行与制品目录。
  3. 再删同一会话，并检查其他会话。
- 预期结果：
  1. 204 无体。
  2. 会话/事件/制品/调用记录全部不可见，文件已进 `.trash` 或删除。
  3. 重复删除 404；其他会话数据完好。
- 边界异常数据：无制品会话；目录重命名失败注入 → 500 `session_delete_failed` 且数据未删。

### TC-031：首页最近 10 条会话与空态
- 测试目的：验证首页复用 `GET /sessions?limit=10` 的排序与空态。
- 测试类型：集成·接口
- 关联需求：AC-001-3；任务 TASK-TD-031 / 044
- 涉及本体：无
- 自动化落点：`tests/test_sessions_api.py::test_tc031_recent_sessions_limit10`；`tests/test_entrances_api.py::test_tc031_home_recent_sessions`
- 前置条件：11 条会话。
- 测试步骤：
  1. `GET /sessions?limit=10`。
  2. 删除全部会话后再请求。
- 预期结果：
  1. 返回 10 条按 `updated_at` 倒序，`nextCursor` 非空。
  2. 返回 `{"items":[],"nextCursor":null}`，前端展示空态而非错误。
- 边界异常数据：恰好 10 条；0 条；会话更新时间相同（按 id 倒序）。

### TC-032：提交文本追加 input_text 事件
- 测试目的：验证文本输入落为事件并可用于后续调用。
- 测试类型：集成·接口
- 关联需求：AC-006-1；任务 TASK-TD-035 / 037
- 涉及本体：无
- 自动化落点：`tests/test_inputs_api.py::test_tc032_append_text_event`
- 前置条件：进行中会话。
- 测试步骤：
  1. `POST /sessions/{id}/inputs/text` 提交标题与正文。
  2. 查询事件列表与事件 payload。
  3. 以该文本为提示发起一次调用。
- 预期结果：
  1. 201 返回事件，`type=input_text`，payload 含 `title/text/charCount`。
  2. 时间线出现该事件。
  3. 调用可用该正文（前端组合提示），事件不被修改。
- 边界异常数据：正文恰好 200000 字符；含 `sk-` 的正文（不得进入调用记录摘要原文）。

### TC-033：空或纯空白正文拒绝
- 测试目的：验证空正文错误与不落事件。
- 测试类型：集成·接口
- 关联需求：AC-006-2；任务 TASK-TD-035 / 037
- 涉及本体：无
- 自动化落点：`tests/test_inputs_api.py::test_tc033_empty_text_rejected`
- 前置条件：进行中会话。
- 测试步骤：
  1. 分别提交 `""`、`"   "`、`"\n\t"`。
  2. 查询事件数。
- 预期结果：
  1. 400 `text_empty`，`details[].field=text`。
  2. 事件数不变。
- 边界异常数据：零宽字符（U+200B）、仅换行；`title` 为空或 201 字符 → 400。

### TC-034：超过 200,000 字符拒绝并给出字数
- 测试目的：验证上限精确、不静默截断。
- 测试类型：集成·接口
- 关联需求：AC-006-3；任务 TASK-TD-035 / 037
- 涉及本体：无
- 自动化落点：`tests/test_inputs_api.py::test_tc034_text_over_limit_rejected`
- 前置条件：进行中会话。
- 测试步骤：
  1. 提交 200000 字符。
  2. 提交 200001 字符。
  3. 检查事件与响应。
- 预期结果：
  1. 201，`charCount=200000`，文本完整。
  2. 400 `text_too_long`，`details` 含 `charCount=200001`、`maxChars=200000`。
  3. 不写事件，不截断保存。
- 边界异常数据：中文/emoji（按 Unicode 字符计）；200000 与 200001 各一。

### TC-035：追加事件刷新会话 updated_at
- 测试目的：验证写入事件后会话更新时间与列表排序变化。
- 测试类型：集成·服务
- 关联需求：AC-006-1；任务 TASK-TD-035
- 涉及本体：无
- 自动化落点：`tests/test_inputs_api.py::test_tc035_updated_at_bumped`
- 前置条件：两个会话。
- 测试步骤：
  1. 记录会话 A `updatedAt`；向 A 追加文本。
  2. 查询会话列表。
- 预期结果：
  1. `updatedAt` 增大。
  2. A 排到列表首位。
- 边界异常数据：同一时钟步长内连续两次追加（需单调增加或至少不减少）。

### TC-036：上传成功、事件、元数据与预览下载
- 测试目的：验证允许类型上传、制品事件、元数据与内容接口。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-007-1；任务 TASK-TD-015 / 036 / 038
- 涉及本体：无
- 自动化落点：`tests/test_artifacts_service.py::test_tc036_save_upload_success`；`tests/test_artifacts_api.py::test_tc036_upload_success_and_preview`
- 前置条件：进行中会话。
- 测试步骤：
  1. 上传 `app.log`。
  2. 查询事件、`GET /artifacts/{id}`、`GET /artifacts/{id}/content`（inline 与 download）。
- 预期结果：
  1. 201 items 含 `fileName/mimeType/byteSize`，无磁盘路径；事件 `type=artifact`。
  2. 元数据正确；content 返回原文，`Content-Type: text/plain`、`X-Content-Type-Options: nosniff`、`Content-Disposition` 正确。
  3. `mode=download` 为 `attachment`；`max_bytes` 默认/上限 262144。
- 边界异常数据：9 种允许扩展名；0 字节与 1 字节文件；`max_bytes` 越界 400。

### TC-037：白名单/大小/数量整批拒绝
- 测试目的：验证上传三查与全有或全无。
- 测试类型：集成·接口
- 关联需求：AC-007-2；任务 TASK-TD-036
- 涉及本体：无
- 自动化落点：`tests/test_artifacts_api.py::test_tc037_batch_validation_rejects_all`
- 前置条件：进行中会话。
- 测试步骤：
  1. 提交含 `.exe` 的混合批次。
  2. 提交 10MB+1 文件。
  3. 提交 11 个文件。
  4. 每次检查制品行与 `sessions/<id>/` 目录。
- 预期结果：
  1. 400 `file_type_not_allowed`；2) 400 `file_too_large`；3) 400 `too_many_files`。
  2. `details` 列出每个不合格文件与原因。
  3. 三次均不落任何制品（含批次中的合法文件）。
- 边界异常数据：10 个文件、恰好 10MB、`.LOG` 大写、`a.txt.exe` 双扩展名。

### TC-038：同名自动改名保留两份
- 测试目的：验证同名上传不覆盖。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-007-3；任务 TASK-TD-015 / 036 / 038
- 涉及本体：无
- 自动化落点：`tests/test_artifacts_service.py::test_tc038_duplicate_name_renamed`；`tests/test_artifacts_api.py::test_tc038_duplicate_names_renamed`
- 前置条件：已上传 `app.log`。
- 测试步骤：
  1. 再上传两个 `app.log`。
  2. 查询三条制品与文件内容。
- 预期结果：
  1. 文件名为 `app-1.log`、`app-2.log`，原名保留。
  2. 三份内容各自独立，不覆盖。
- 边界异常数据：改名到上限 100；中文文件名；大小写不同的同名。

### TC-039：路径穿越与符号链接拒绝
- 测试目的：验证存储层路径解析与 API 文件名注入防护。
- 测试类型：单元（storage）+ 集成·接口
- 关联需求：AC-007-2（RISK-005）；任务 TASK-TD-012 / 036
- 涉及本体：无
- 自动化落点：`tests/test_storage.py::test_tc039_path_traversal_rejected`；`tests/test_artifacts_api.py::test_tc039_traversal_rejected_via_api`
- 前置条件：会话目录存在。
- 测试步骤：
  1. `safe_artifact_path` 传入 `../../x`、`..%2F..%2Fx`、绝对路径、Windows `..\\x`。
  2. 在会话目录内放符号链接指向外部文件后读取。
  3. multipart 文件名传 `../../etc/passwd`。
- 预期结果：
  1. 全部拒绝（not found / 400），不读到会话目录外文件。
  2. 符号链接被拒绝。
  3. 落盘名为 `<uuid4hex>.<ext>`，原名只存库。
- 边界异常数据：Unicode 归一化等价路径、大小写差异路径。

### TC-040：磁盘失败 507、无残留与无 DB 行
- 测试目的：验证写入失败时的清理与错误映射。
- 测试类型：单元（storage）+ 集成·接口（故障注入）
- 关联需求：AC-007-1（RISK-006）；任务 TASK-TD-012 / 036
- 涉及本体：无
- 自动化落点：`tests/test_storage.py::test_tc040_storage_cleanup_on_failure`；`tests/test_artifacts_api.py::test_tc040_disk_failure_returns_507`
- 前置条件：进行中会话。
- 测试步骤：
  1. monkeypatch 写入中途抛 `OSError`。
  2. 检查 `.tmp`、`sessions/<id>/`、`artifact` 行与事件。
- 预期结果：
  1. 507 `artifact_write_failed`。
  2. 无临时文件、无半成品、无 `artifact` 行、无 `artifact` 事件。
  3. 会话 `updated_at` 不变。
- 边界异常数据：移动阶段失败；长文件名；磁盘满模拟（ENOSPC）。

### TC-041：成功调用返回文本与 callId、写记录与事件
- 测试目的：验证统一模型出口的成功路径。
- 测试类型：集成·服务 + 接口（假适配器）
- 关联需求：AC-005-1；任务 TASK-TD-016 / 039 / 040
- 涉及本体：无
- 自动化落点：`tests/test_ai_gateway.py::test_tc041_success_records_call`；`tests/test_calls_api.py::test_tc041_api_call_success`
- 前置条件：进行中会话 + 启用模型。
- 测试步骤：
  1. 发起调用，假适配器返回固定文本。
  2. 查询 `ai_call_record`、事件时间线与会话。
- 预期结果：
  1. 200 含 `callId/resultText/latencyMs/retryCount=0/model`。
  2. 一条 `status=success` 记录（模型快照、`prompt_digest`、`latency_ms`），一条 `call` 事件，会话 `updated_at` 刷新。
- 边界异常数据：提示 1 字符与 200000 字符；上游返回空文本（按 `ai_invalid_request` 或成功空串，需在用例固定）。

### TC-042：上游失败记录并可读错误
- 测试目的：验证失败调用留痕与错误映射。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-005-2；任务 TASK-TD-016 / 017 / 039
- 涉及本体：无
- 自动化落点：`tests/test_ai_gateway.py::test_tc042_upstream_failure_recorded`；`tests/test_ai_adapters.py::test_tc042_adapter_error_mapping`；`tests/test_calls_api.py::test_tc042_api_call_failure`
- 前置条件：进行中会话。
- 测试步骤：
  1. 模拟上游 401、429、500、400。
  2. 检查响应、`ai_call_record` 与事件。
- 预期结果：
  1. 502 `ai_auth` / `ai_rate_limit` / `ai_server_error` / `ai_invalid_request`，`details` 含 `callId`、`retryCount`。
  2. 每条失败都有记录（`status=failed`、`error_code`、`error_message`），错误信息可读且不含密钥。
- 边界异常数据：错误体回显 `Authorization` 或 `sk-` 的响应（必须脱敏）。

### TC-043：前置拒绝不产生调用记录
- 测试目的：验证 AC-005-3 的「发起外部请求前拒绝且无记录」。
- 测试类型：集成·接口
- 关联需求：AC-005-3；任务 TASK-TD-039
- 涉及本体：无
- 自动化落点：`tests/test_calls_api.py::test_tc043_precondition_rejections_no_record`
- 前置条件：构造不存在会话、已完成会话、停用模型、停用提供商、超长提示。
- 测试步骤：
  1. 分别发起五类请求。
  2. 统计 `ai_call_record` 与假适配器调用次数。
- 预期结果：
  1. 404 `session_not_found`；409 `session_closed` / `model_disabled` / `provider_disabled`；400 `prompt_too_long`。
  2. 记录数 0，外部适配器调用 0 次。
- 边界异常数据：提示 200001 字符；模型停用但提供商启用；提供商停用。

### TC-044：时间线与详情展示摘要且无密钥
- 测试目的：验证调用结果在会话详情中的可见内容与脱敏。
- 测试类型：集成·接口
- 关联需求：AC-005-4；任务 TASK-TD-034 / 039 / 040
- 涉及本体：无
- 自动化落点：`tests/test_calls_api.py::test_tc044_call_event_payload`
- 前置条件：一次成功调用与一次失败调用。
- 测试步骤：
  1. 请求会话详情与事件列表。
  2. 检查 `call` 事件 payload 与 `promptDigest`/预览。
- 预期结果：
  1. 展示模型、耗时、状态与提示摘要。
  2. 摘要不含完整提示原文与任何密钥；失败事件含错误码与重试次数。
- 边界异常数据：超长提示截断；含 `sk-` 的提示。

### TC-045：重试 1 次、超时不重试、取消终结
- 测试目的：验证重试策略与超时语义。
- 测试类型：集成·服务 + 接口（时钟/假适配器）
- 关联需求：AC-005-5；任务 TASK-TD-016 / 039 / 047
- 涉及本体：无
- 自动化落点：`tests/test_ai_gateway.py::test_tc045_retry_then_timeout`；`tests/test_ai_gateway.py::test_tc045_cancellation_finalizes_record`；`tests/test_calls_api.py::test_tc045_api_retry_and_timeout`
- 前置条件：假适配器可编程失败次数与时延；`AW_AI_MAX_CONCURRENCY=1`。
- 测试步骤：
  1. 第一次 500、第二次成功。
  2. 两次都 500。
  3. 单次尝试超过 120s。
  4. 调用任务被取消。
- 预期结果：
  1. 成功且 `retryCount=1`。
  2. 502 `ai_server_error`，`retryCount=1`，只重试 1 次。
  3. 504 `ai_timeout`，`status=timeout`，不重试。
  4. 取消后记录终结为 `failed(interrupted)`；排队等待不计入 `latencyMs`。
- 边界异常数据：网络错误与 5xx 混合；409/400 不重试；120s 前后 1 秒。

### TC-046：按会话/项目/时间查询倒序
- 测试目的：验证调用记录查询的筛选、排序与游标。
- 测试类型：集成·接口
- 关联需求：AC-010-1；任务 TASK-TD-042 / 043
- 涉及本体：无
- 自动化落点：`tests/test_calls_query.py::test_tc046_query_calls_ordering`
- 前置条件：两个项目、多条成功/失败/超时记录。
- 测试步骤：
  1. 按 `sessionId`、`projectId`、`status`、`from`/`to` 筛选。
  2. 用 `limit=2` 翻页。
- 预期结果：
  1. 只返回匹配项，`created_at DESC, call_id DESC`。
  2. 列表项不含 `resultText`；翻页不重不漏。
- 边界异常数据：相同 `created_at` 按 `call_id` 倒序；非法时间格式 400；未来时间返回空。

### TC-047：失败详情含错误与重试次数、无密钥
- 测试目的：验证失败记录可核对。
- 测试类型：集成·接口
- 关联需求：AC-010-2；任务 TASK-TD-042 / 043
- 涉及本体：无
- 自动化落点：`tests/test_calls_query.py::test_tc047_failed_call_detail`
- 前置条件：存在失败记录。
- 测试步骤：
  1. `GET /calls/{callId}`。
  2. 检查字段。
- 预期结果：
  1. 200 含 `errorCode`、`errorMessage`、`retryCount`。
  2. 不含密钥、提示原文；404 `call_not_found` 用于不存在 id。
- 边界异常数据：超时记录 `retryCount=0`；成功记录含 `resultText`。

### TC-048：无匹配返回空列表而非错误
- 测试目的：验证空态语义。
- 测试类型：集成·接口
- 关联需求：AC-010-3；任务 TASK-TD-042 / 043
- 涉及本体：无
- 自动化落点：`tests/test_calls_query.py::test_tc048_empty_result_not_error`
- 前置条件：已登录、无匹配数据。
- 测试步骤：
  1. 用不存在的项目/时间范围筛选。
  2. 检查响应与前端空态（Vitest 第二实现）。
- 预期结果：
  1. 200 `{"items":[],"nextCursor":null}`。
  2. 前端展示空态，不展示错误提示。
- 边界异常数据：空状态筛选；`from` 晚于 `to` 400。

### TC-049：启动归并 running → failed(interrupted)
- 测试目的：验证重启后的记录终结与清理。
- 测试类型：集成·服务
- 关联需求：AC-005-1；任务 TASK-TD-013 / 047
- 涉及本体：无
- 自动化落点：`tests/test_startup.py::test_tc049_startup_merges_running_calls`；`tests/test_startup.py::test_tc049_restart_merges_running`
- 前置条件：库中插入 `running` 记录；存在过期登录会话与失败计数。
- 测试步骤：
  1. 执行启动自检/归并。
  2. 检查记录、事件与会话。
- 预期结果：
  1. 记录变为 `failed(interrupted)`，`finished_at`、`latency_ms` 非空。
  2. 时间线新增 `call` 事件，会话仍可继续输入。
  3. 过期登录会话与超窗失败计数被清理。
- 边界异常数据：无 running 记录（no-op）；数据库不可用 → 启动失败非 0 退出。

### TC-050：凭据解密失败 502 且无记录
- 测试目的：验证密钥不可用时不进入上游、不产生记录。
- 测试类型：集成·服务 + 接口
- 关联需求：AC-005-2；任务 TASK-TD-025 / 039
- 涉及本体：无
- 自动化落点：`tests/test_providers_service.py::test_tc050_credential_decrypt_failure_no_record`；`tests/test_calls_api.py::test_tc050_api_credential_unavailable`
- 前置条件：提供商密文被篡改或 `AW_ENCRYPTION_KEY` 轮换。
- 测试步骤：
  1. 发起调用。
  2. 执行连接测试。
- 预期结果：
  1. 502 `provider_credential_unavailable`，`ai_call_record` 0 行。
  2. 连接测试 `ok=false, errorCode=credential_unavailable`；两者均不含密文。
- 边界异常数据：错误密钥、`v2:` 前缀、空密文。

### TC-051：6 个入口含名称与用途
- 测试目的：验证入口配置唯一来源与接口输出。
- 测试类型：单元 + 集成·接口
- 关联需求：AC-001-1；任务 TASK-TD-003 / 044
- 涉及本体：无
- 自动化落点：`tests/test_entrances.py::test_tc051_entrances_has_six_items`；`tests/test_entrances_api.py::test_tc051_api_entrances_six`
- 前置条件：已登录。
- 测试步骤：
  1. 读取 `core.entrances` 常量。
  2. `GET /api/v1/entrances`。
- 预期结果：
  1. 恰好 6 项，key 为 `case-library`、`bug-analysis`、`log-triage`、`sql-analysis`、`regression-list`、`test-report`。
  2. 每项含 `name`、`description`、`domain`、`status`；本期 `status=planned`；首页渲染 6 卡片。
- 边界异常数据：key 唯一；名称不含「生成测试用例」。

### TC-052：入口路由刷新直达（SPA fallback）
- 测试目的：验证深链接刷新不 404、鉴权顺序正确。
- 测试类型：集成·接口
- 关联需求：AC-001-2；任务 TASK-TD-044
- 涉及本体：无
- 自动化落点：`tests/test_entrances_api.py::test_tc052_spa_fallback_entrance_route`
- 前置条件：前端构建产物存在（CI/本地构建后）；已登录。
- 测试步骤：
  1. 直接 GET `/entrances/bug-analysis`（HTML）。
  2. 未登录访问同一路径。
- 预期结果：
  1. 200 返回 `index.html`，路由由前端接管。
  2. 302 `/login?next=%2Fentrances%2Fbug-analysis`。
- 边界异常数据：带查询串与锚点；静态资源路径不应回退到 index.html。

### TC-053：未知入口 key 拒绝
- 测试目的：验证入口 key 白名单。
- 测试类型：集成·接口
- 关联需求：AC-001-2；任务 TASK-TD-044
- 涉及本体：无
- 自动化落点：`tests/test_entrances_api.py::test_tc053_unknown_entrance_rejected`
- 前置条件：已登录。
- 测试步骤：
  1. 请求 `GET /entrances/unknown`、`/entrances/Case-Library`。
  2. 检查响应与副作用。
- 预期结果：
  1. 400 `entrance_unknown`（大小写敏感，仅接受固定 key）。
  2. 不创建会话、不产生记录。
- 边界异常数据：空 key、URL 编码 key、超长 key。

### TC-054：占位页说明所属域、状态与返回入口
- 测试目的：验证未交付入口的占位信息完整。
- 测试类型：集成·接口
- 关联需求：AC-002-1；任务 TASK-TD-045
- 涉及本体：无
- 自动化落点：`tests/test_entrances_api.py::test_tc054_placeholder_metadata`
- 前置条件：入口 `status=planned`。
- 测试步骤：
  1. 请求入口配置与占位页路由。
  2. 检查页面文案。
- 预期结果：
  1. 含所属域名称、状态说明与返回首页入口。
  2. 不出现可提交输入的控件。
- 边界异常数据：6 个入口逐一检查；状态文案与配置一致。

### TC-055：占位页无副作用
- 测试目的：验证停留在/刷新占位页不创建数据。
- 测试类型：集成·接口
- 关联需求：AC-002-2；任务 TASK-TD-045
- 涉及本体：无
- 自动化落点：`tests/test_entrances_api.py::test_tc055_placeholder_has_no_side_effects`
- 前置条件：记录四张表行数。
- 测试步骤：
  1. 连续访问占位页 3 次（模拟刷新）。
  2. 再次统计 `analysis_session`、`session_event`、`ai_call_record`。
- 预期结果：
  1. 行数不变；无模型调用。
  2. 不产生制品文件。
- 边界异常数据：未登录访问（应跳登录，也不产生数据）。

### TC-056：入口 planned/live 由配置驱动
- 测试目的：验证状态切换不需要改代码。
- 测试类型：单元 + 集成·接口
- 关联需求：AC-002-3；任务 TASK-TD-003 / 045
- 涉及本体：无
- 自动化落点：`tests/test_entrances.py::test_tc056_entrance_status_is_config_driven`；`tests/test_entrances_api.py::test_tc056_entrance_status_switch`
- 前置条件：可覆盖入口配置。
- 测试步骤：
  1. 把某入口状态改为 `live`。
  2. 请求入口配置与入口页。
- 预期结果：
  1. `GET /entrances` 返回 `live`。
  2. 页面渲染 live 挂载点而非占位文案。
- 边界异常数据：非法状态值在加载时被拒绝；缺配置显示错误态。

### TC-057：四个冻结签名契约与配置契约
- 测试目的：锁定 `sessions.create` / `sessions.append_event` / `artifacts.save` / `AiGateway.complete` 的签名与语义。
- 测试类型：契约
- 关联需求：AC-TECH-1；任务 TASK-TD-002 / 014 / 015 / 016
- 涉及本体：无
- 自动化落点：`tests/test_config.py::test_tc057_frozen_settings_contract`；`tests/test_sessions_service.py::test_tc057_frozen_session_signatures`；`tests/test_artifacts_service.py::test_tc057_frozen_artifact_signature`；`tests/test_ai_gateway.py::test_tc057_frozen_gateway_signature`
- 前置条件：模块可导入。
- 测试步骤：
  1. `inspect.signature` 比对参数名、顺序、仅关键字参数。
  2. 按 `change-spec.md` 示例调用四个签名。
  3. 传入多余位置参数/未知关键字。
- 预期结果：
  1. 签名与冻结契约完全一致。
  2. 示例调用成功并返回约定结构。
  3. 额外参数抛 `TypeError`，不被静默接受。
- 边界异常数据：`AiGateway.complete` 的 `prepared` 长度 0/200001；`append_event` 的未知事件类型。

### TC-058：SQLite 空库迁移到 head 且模型与文档一致
- 测试目的：验证 10 张表与 5 个 revision 的迁移完整性。
- 测试类型：集成·迁移
- 关联需求：AC-TECH-2；任务 TASK-TD-007 / 008 / 009 / 010 / 018
- 涉及本体：无
- 自动化落点：`tests/test_engine.py::test_tc058_engine_creation_both_dialects`；`tests/test_db_migrations.py::test_tc058_models_match_schema_metadata`；`tests/test_db_migrations.py::test_tc058_migrate_empty_db_to_head`
- 前置条件：空临时库。
- 测试步骤：
  1. `alembic upgrade head`。
  2. 检查 `alembic_version` 与 10 张表。
  3. 比对 ORM 元数据与库结构（列、类型、空值、默认值、CHECK、唯一、索引、外键）。
  4. `downgrade base` 后再 `upgrade head`。
- 预期结果：
  1. 升级成功，version 为 head（`0005_ai_call_record`）。
  2. 10 张表齐全，约束与 `database-schema.md` 一致。
  3. 降级/再升级无残留错误。
- 边界异常数据：重复 `upgrade head` 幂等；应用启动只校验不自动迁移。

### TC-059：MySQL 关键约束复验（SQLite 本地必须可跑）
- 测试目的：验证唯一、CHECK、级联、RESTRICT、大小写归一在两类方言一致。
- 测试类型：集成·迁移（双方言）
- 关联需求：AC-TECH-2；任务 TASK-TD-009 / 010 / 018
- 涉及本体：无
- 自动化落点：`tests/test_db_migrations.py::test_tc059_constraints_on_test_database`
- 前置条件：`AW_TEST_DATABASE_URL` 未设置时在 SQLite 上执行通用约束断言；设置时复跑并追加方言断言。
- 测试步骤：
  1. 项目名大小写重复插入 → 唯一冲突。
  2. 非法 `status`/`entrance_key`/`protocol` 插入 → CHECK 失败。
  3. 删除 `analysis_session` → 事件/制品/记录级联；删除被引用项目 → RESTRICT。
- 预期结果：
  1. 唯一约束在 SQLite 与 MySQL 均生效（`utf8mb4_bin` + `casefold`）。
  2. CHECK 生效。
  3. 级联与 RESTRICT 与文档一致。
  4. 本地用例不得因缺少 MySQL 而整体 skip（保证 `aw verify` 能看到 TC-059 结果）；MySQL 独有断言由 CI job 2 提供证据。
- 边界异常数据：大小写混合、全角字符、超长索引键。

### TC-060：错误体、requestId 与游标分页契约
- 测试目的：验证统一错误体与分页参数边界。
- 测试类型：集成·接口
- 关联需求：AC-TECH-3；任务 TASK-TD-011
- 涉及本体：无
- 自动化落点：`tests/test_api_skeleton.py::test_tc060_error_envelope_and_cursor`
- 前置条件：已登录。
- 测试步骤：
  1. 触发 400（字段错误）与 404。
  2. 检查 `requestId` 唯一性。
  3. 测试 `limit=1/100/0/101` 与伪造 `cursor`。
  4. `DELETE` 成功响应。
- 预期结果：
  1. 错误体恒为 `{code,message,details[],requestId}`，字段错误带 `field`。
  2. `requestId` 每次不同、不含敏感信息。
  3. `limit` 越界 400；游标 base64url 往返；伪造游标 400。
  4. 204 无响应体。
- 边界异常数据：事件列表 `limit=200/201`；空 `details`；非 JSON 请求体。

### TC-061：Origin/Referer 校验 403
- 测试目的：验证 CSRF 防护（RISK-013）。
- 测试类型：集成·接口
- 关联需求：AC-TECH-3、AC-011-1；任务 TASK-TD-011 / 020
- 涉及本体：无
- 自动化落点：`tests/test_api_skeleton.py::test_tc061_origin_check_rejects_cross_site`
- 前置条件：`AW_PUBLIC_ORIGIN=http://testserver`。
- 测试步骤：
  1. `POST /auth/login` 与 `POST /sessions` 不带 Origin/Referer。
  2. 带 `Origin: https://evil.example`。
  3. 带同源 Origin，以及只带同源 Referer。
  4. 用 GET 请求。
- 预期结果：
  1. 缺失 403 `forbidden_origin`。
  2. 错误来源 403。
  3. 同源放行；Referer 回退生效。
  4. GET 不受影响。
- 边界异常数据：`Origin: null`、带端口/尾斜杠的同源、多值 Origin。

### TC-062：批次 B 最小闭环冒烟
- 测试目的：验证批次 A+B 可独立跑通最小闭环。
- 测试类型：集成·冒烟
- 关联需求：AC-TECH-4；任务 TASK-TD-041
- 涉及本体：无
- 自动化落点：`tests/test_batch_b_smoke.py::test_tc062_batch_b_minimal_loop`
- 前置条件：全新空库 + 假 AI 适配器；不依赖浏览器与外网。
- 测试步骤：
  1. 登录 → 建项目 → 配提供商 → 建模型 → 建会话 → 贴文本 → 发起调用。
  2. 查询会话详情、事件、调用记录。
- 预期结果：
  1. 各步 200/201，Cookie 建立。
  2. 时间线含 `input_text` 与 `call`；`ai_call_record` 一行 success。
  3. 会话 `updated_at` 变化。
- 边界异常数据：仅需批次 A+B 的端点，不调用批次 C 的 `/calls` 查询与入口占位页。

### TC-063：日志、响应与记录中无密钥与口令
- 测试目的：验证脱敏过滤器与响应 schema（RISK-001 / RISK-012）。
- 测试类型：单元（redaction）+ 集成·接口
- 关联需求：AC-TECH-6、AC-003-1、AC-011-3；任务 TASK-TD-006
- 涉及本体：无
- 自动化落点：`tests/test_redaction.py::test_tc063_logs_and_responses_never_contain_secrets`
- 前置条件：捕获 caplog；构造含 `Authorization`、`Cookie`、`sk-`、口令的请求与上游错误。
- 测试步骤：
  1. 直接调用 `redact()` 与 logging Filter。
  2. 走登录失败、提供商创建、连接测试、调用成功、调用失败、未捕获异常。
  3. 汇总所有响应体与日志。
- 预期结果：
  1. 敏感键值替换为 `[REDACTED]`，超长文本截断。
  2. 所有响应与日志不含口令、令牌原文、API 密钥原文与密文。
  3. `AiCallRecord` 摘要不含密钥。
- 边界异常数据：SDK 异常文本携带密钥；多行 JSON 日志；嵌套字典。

### TC-064：迁移 0006 的知识库注入四列与 CHECK，且先于 knowledge-base 0007
- 测试目的：验证 `ai_call_record` 四列、`session_event.type` 的 CHECK 扩展与迁移顺序约束。
- 测试类型：集成·迁移（SQLite 本地；MySQL 由 CI job 2）
- 关联需求：AC-TECH-2；任务 TASK-TD-051 / 055
- 涉及本体：无
- 自动化落点：`tests/test_db_migrations.py::test_tc064_migration_0006_injection_columns`；`tests/test_db_migrations.py::test_tc064_migration_order_before_knowledge_base`
- 前置条件：空临时库；迁移树含 `0001` ~ `0006`。
- 测试步骤：
  1. `alembic upgrade head`，检查 `alembic_version` 与 `ai_call_record` 列。
  2. 插入 `total_chars != prompt_chars + injected_chars` 的行。
  3. `downgrade` 到 `0005` 再升级；检查空库升级未创建 `knowledge_base` 表。
- 预期结果：
  1. head 为 `0006_knowledge_injection`；四列为 `knowledge_injection`（JSON NULL）、`injected_chars`/`prompt_chars`/`total_chars`（Integer NOT NULL default 0）。
  2. CHECK 拒绝不一致的行；`session_event.type=knowledge_injection` 可插入，非法类型仍被拒。
  3. `0006` 的 `down_revision` 指向 `0005`；空库升级不创建 `knowledge_base`；`0007` 属 knowledge-base spec，不在本 spec 出现。
- 边界异常数据：负数 `injected_chars`/`prompt_chars`；`total_chars` 为 NULL；重复升级 head 幂等。

### TC-065：`injection=None` 时记录与事件与扩展前完全一致
- 测试目的：验证知识库注入是可选扩展，不改变既有调用链。
- 测试类型：集成·服务（假适配器）
- 关联需求：AC-005-1；任务 TASK-TD-052
- 涉及本体：无
- 自动化落点：`tests/test_ai_gateway_injection.py::test_tc065_no_injection_preserves_baseline`
- 前置条件：进行中会话 + 启用模型；不传 `injection`。
- 测试步骤：
  1. 调用 `AiGateway.complete(session_id, model_id, prepared)`。
  2. 查询 `ai_call_record`、`session_event` 与会话。
  3. 对照扩展前的基线断言（与 TC-041 同一组断言）。
- 预期结果：
  1. 记录中 `knowledge_injection IS NULL`，`injected_chars=0`，`total_chars=prompt_chars=prompt_char_count=len(prepared)`。
  2. 只有一条 `call` 事件，无 `knowledge_injection` 事件。
  3. 会话 `updated_at`、状态与 `retry_count` 行为不变。
- 边界异常数据：`prepared` 1 字符与 200000 字符；上游失败/超时路径同样不产生注入列与事件。

### TC-066：注入时同事务写四列与 `knowledge_injection` 事件，失败/超时保留
- 测试目的：验证注入留痕的原子性与失败保留语义。
- 测试类型：集成·服务（假适配器）
- 关联需求：AC-005-1；任务 TASK-TD-052
- 涉及本体：无
- 自动化落点：`tests/test_ai_gateway_injection.py::test_tc066_injection_persisted_and_survives_failure`
- 前置条件：构造 `InjectionSnapshot`（items 与 `injected_chars`、`prompt_chars`、`total_chars` 自洽）。
- 测试步骤：
  1. 传入快照成功调用。
  2. 传入快照触发上游 500（重试后仍失败）与 120s 超时。
  3. 传入不一致快照（`injected_chars`/`total_chars`/`len(prepared)`）。
- 预期结果：
  1. 记录四列与快照一致，`knowledge_injection` JSON 只含 `kbId/kbName/kbVersion/entryCodes/injectedChars`（无正文）；同一事务追加 `knowledge_injection` 事件。
  2. 失败与超时记录保留四列与事件，`status=failed|timeout` 正常终结。
  3. 不一致快照抛 `injection_snapshot_mismatch`，不写记录、不追加事件、不发起外部请求。
- 边界异常数据：空 items（`injected_chars=0`）；`excludedCodes` 非空；中断（取消）时保留留痕。

### TC-067：调用记录序列化 `knowledgeInjection` 与 `kbDeleted`
- 测试目的：验证列表与详情的注入快照序列化及读取时 `kbDeleted` 计算。
- 测试类型：集成·接口
- 关联需求：AC-010-2；任务 TASK-TD-052
- 涉及本体：无
- 自动化落点：`tests/test_calls_api.py::test_tc067_knowledge_injection_serialization`
- 前置条件：两条记录：无注入、有注入；后者 `kbId=5`。
- 测试步骤：
  1. `GET /api/v1/calls` 与 `GET /api/v1/calls/{callId}`。
  2. 在 `knowledge_base` 表（测试内手动建）插入 `kbId=5` 后复测。
  3. 删除该行后再测；再 drop 表后测。
- 预期结果：
  1. 无注入记录 `knowledgeInjection=null`；有注入记录含 `kbId/kbName/kbVersion/entryCodes/injectedChars/kbDeleted`。
  2. 行存在 → `kbDeleted=false`；行删除 → `true`；表不存在 → `true`。
  3. 历史快照字段不因知识库删除而改写；列表仍不返回 `resultText`。
- 边界异常数据：多条 kb；`entryCodes` 空数组；`knowledge_base` 表存在但列为空。

### TC-068：失效条目未精确确认 → 409，且无外部请求、无 AiCallRecord
- 测试目的：验证 `knowledge_invalid_entries` 的确认语义与前置拒绝。
- 测试类型：集成·接口（假 `InjectionPreparer`）+ 契约
- 关联需求：AC-TECH-3（A103 B）；任务 TASK-TD-053 / 055
- 涉及本体：无
- 自动化落点：`tests/test_sessions_ai_complete.py::test_tc068_invalid_entries_require_confirmation`；`tests/test_knowledge_contract.py::test_tc068_preparer_contract`
- 前置条件：注册假 preparer，返回失效集 `[{kbId:5, code:"ENT-009", reason:"…"}]`；进行中会话。
- 测试步骤：
  1. `POST /api/v1/sessions/{id}/ai/complete` 带 `knowledgeRefs`，不带 `confirmInvalidCodes`。
  2. 带部分确认（少一个 code）重试。
  3. 用 `InjectionPreparer` 协议的假实现校验入参/返回类型。
- 预期结果：
  1. 409 `knowledge_invalid_entries`，`details.invalidItems` 与失效集一致；无 `ai_call_record`，假适配器调用 0 次。
  2. 部分确认仍 409（要求完全相等），仍无记录与外部请求。
  3. 契约签名（入参 refs/confirm、返回 prepared + snapshot）与 `change-spec.md` §3.3 一致。
- 边界异常数据：失效集为空但带 confirm；多 kb 各自失效；重复 code。

### TC-069：精确确认后调用；空集 409、超预算 400
- 测试目的：验证确认后成功注入与空集/预算边界的拒绝。
- 测试类型：集成·接口（假 preparer）
- 关联需求：AC-TECH-3（A103 B）；任务 TASK-TD-053
- 涉及本体：无
- 自动化落点：`tests/test_sessions_ai_complete.py::test_tc069_confirmed_injection_and_limits`
- 前置条件：假 preparer 可返回成功/空集/超预算；`AW_PROMPT_MAX_CHARS=200000`。
- 测试步骤：
  1. 带精确 `confirmInvalidCodes` 调用成功。
  2. 确认后有效集为空。
  3. 提示 + 注入块合计 200001 字符。
  4. 未安装 preparer 时带 `knowledgeRefs` 调用。
- 预期结果：
  1. 200，`knowledgeInjection` 非空，`prepared` 与快照一致；记录四列与事件写入。
  2. 409 `knowledge_injection_empty`，无记录、无外部请求。
  3. 400 `prompt_budget_exceeded`，`details={promptChars,injectedChars,totalChars,limit}`；无记录。
  4. 409 `knowledge_unavailable`，无记录、无外部请求。
- 边界异常数据：合计恰好 200000 通过；注入块 0 字符；不传 `knowledgeRefs` 时行为同 TC-065。

### TC-070：时间线与调用详情展示注入快照与「知识库已删除」
- 测试目的：验证注入快照在会话时间线与调用记录详情中的可见字段与删除标记。
- 测试类型：集成·接口（pytest 权威）+ Vitest 组件第二实现
- 关联需求：AC-009-3、AC-010-2；任务 TASK-TD-054
- 涉及本体：无
- 自动化落点：`tests/test_sessions_api.py::test_tc070_knowledge_injection_timeline_payload`；Vitest `web/src/features/sessions/KnowledgeInjectionEventCard.test.tsx`（标题带 TC-070，结果不进 `aw verify`）
- 前置条件：一条带注入的成功调用；`knowledge_base` 行可删。
- 测试步骤：
  1. `GET /sessions/{id}/events`，检查 `knowledge_injection` 事件 payload。
  2. `GET /calls/{callId}`，检查 `knowledgeInjection`。
  3. 删除 `knowledge_base` 行后复测。
  4. Vitest 渲染 `KnowledgeInjectionEventCard` 与调用记录行。
- 预期结果：
  1. 事件 payload 含 `items[{kbId,kbName,kbVersion,entryCodes,injectedChars,kbDeleted}]`、`promptChars/injectedChars/totalChars/excludedCodes`，不含正文。
  2. 详情字段与事件一致；删除后 `kbDeleted=true`，前端标「知识库已删除」。
  3. 无注入时不渲染该卡片；不新增样式变量。
- pytest 与 CI 的覆盖边界：pytest 覆盖事件 payload、详情序列化与 `kbDeleted` 布尔值；Vitest 覆盖卡片渲染、文案与「无注入不渲染」，只由 CI job 3 报告，`aw verify` 不读取；卡片视觉与双主题由人工 M-01 复核。
- 边界异常数据：多 kb 条目排序；`excludedCodes` 非空展示；`kbDeleted` 表不存在。

### TC-071：数据库约束错误映射的方言可移植性
- 测试目的：验证 MySQL 与 SQLite 的驱动异常被统一映射为 400/409/500，不泄露原始约束文本，且两类方言行为一致。
- 测试类型：集成·接口（方言错误桩）
- 关联需求：无独立功能 AC；挂在 AC-TECH-2（双方言迁移与运行）、AC-TECH-3（HTTP 错误契约）与 RISK-011（双方言漂移）下；任务 TASK-TD-011
- 涉及本体：无
- 自动化落点：`tests/test_db_error_mapping.py::test_tc071_db_error_mapping_is_dialect_portable`
- 前置条件：`create_app` 可启动；注入携带 errno 的 `DBAPIError` 桩（MySQL 3819 / 1062 / 1451 / 1452、SQLite CHECK 文本、连接中断 2006）。
- 测试步骤：
  1. 触发 MySQL CHECK 违例（3819）与 SQLite CHECK 违例。
  2. 触发 MySQL 重复键（1062）与外键违例（1451/1452）。
  3. 触发连接中断（2006）。
  4. 检查各响应状态、`code`、`requestId` 与 `X-Request-Id`。
- 预期结果：
  1. 两类方言的 CHECK 违例均为 400，`message` 为通用文案，不含约束名与原始 SQL。
  2. 重复键与外键违例均为 409（`code=conflict`）。
  3. 连接中断为 500 `internal_error`，不含堆栈与驱动原文。
  4. 所有响应仍为 `{code, message, details[], requestId}`，`requestId` 与响应头一致。
- 边界异常数据：未知 errno、errno 为字符串、`orig` 缺失时回退 500；错误体不得回显表名与键值。
- 实现观察：400 的 `code` 字段与 `api-spec.md` 错误码表一致（2026-11-18 按文件字节复核，见 DATA-006）；未发现契约差异。
- CI 证据：本条源于 CI `mysql-tests` job 暴露的方言差异（MySQL 3819/1062/1451/1452 与 SQLite CHECK 文本不同），本地只跑 SQLite 看不到这些错误码，说明「本地 SQLite 绿」不等于双方言通过，CI 第二 job 是必需证据。

## 覆盖矩阵（TC ↔ AC ↔ 任务）

> 覆盖定义：每个 AC 至少一个 TC（正向 + 异常要求见 AC-QA-2）。执行状态在开发完成后由 `aw verify` 回填，当前全部为「已定义、待执行」。
> AC-TECH-5 是任务粒度/格式要求，由 `aw.py check --phase tech-tasks` 与任务结构评审证明，不设运行时 TC（Q-TV-01 已于 2026-11-18 11:23 确认 A）。

| TC | 关联 AC | 主要任务 | pytest 落点（文件::用例） | 覆盖状态 |
|----|---------|---------|--------------------------|---------|
| TC-001 | AC-011-1 | 019/020/021 | test_auth_service.py::test_tc001_unauthorized_without_session；test_auth_api.py::test_tc001_api_401_and_html_redirect | ⏳ 待执行 |
| TC-002 | AC-011-2 | 005/019/020 | test_password.py::test_tc002_password_verify_contract；test_auth_service.py::test_tc002_login_issues_token_hash_only | ⏳ 待执行 |
| TC-003 | AC-011-3 | 019 | test_auth_service.py::test_tc003_wrong_password_uniform_error | ⏳ 待执行 |
| TC-004 | AC-011-4 | 019 | test_auth_service.py::test_tc004_lock_after_five_failures | ⏳ 待执行 |
| TC-005 | AC-011-4 | 019 | test_auth_service.py::test_tc005_concurrent_failures_counted | ⏳ 待执行 |
| TC-006 | AC-011-5 | 019 | test_auth_service.py::test_tc006_idle_expiry_and_refresh | ⏳ 待执行 |
| TC-007 | AC-011-6 | 019/020 | test_auth_service.py::test_tc007_logout_revokes_token | ⏳ 待执行 |
| TC-008 | AC-011-7 | 020/021 | test_auth_api.py::test_tc008_cookie_attributes | ⏳ 待执行 |
| TC-009 | AC-011-2 | 002 | test_config.py::test_tc009_missing_admin_password_refuses_start | ⏳ 待执行 |
| TC-010 | AC-011-1 | 020/021 | test_auth_api.py::test_tc010_login_next_is_internal_only | ⏳ 待执行 |
| TC-011 | AC-011-5 | 020 | test_auth_api.py::test_tc011_expired_session_redirects | ⏳ 待执行 |
| TC-012 | AC-011-1 | 020 | test_auth_api.py::test_tc012_next_rejects_external_url | ⏳ 待执行 |
| TC-013 | AC-008-1 | 022/023/024 | test_projects_service.py::test_tc013_create_project_and_duplicate；test_projects_api.py::test_tc013_api_create_and_conflict | ⏳ 待执行 |
| TC-014 | AC-008-2 | 022/023/024 | test_projects_service.py::test_tc014_update_reflects_and_touches；test_projects_api.py::test_tc014_api_patch | ⏳ 待执行 |
| TC-015 | AC-008-3 | 023 | test_projects_api.py::test_tc015_session_requires_project | ⏳ 待执行 |
| TC-016 | AC-008-1 | 022/023/024 | test_projects_service.py::test_tc016_name_validation；test_projects_api.py::test_tc016_api_validation_fields | ⏳ 待执行 |
| TC-017 | AC-003-1 | 004/025/026/028 | test_crypto.py::test_tc017_crypto_roundtrip_and_tamper；test_providers_service.py::test_tc017_provider_key_encrypted_and_masked；test_providers_api.py::test_tc017_api_never_returns_secret | ⏳ 待执行 |
| TC-018 | AC-003-2 | 025/026/028 | test_providers_service.py::test_tc018_provider_validation；test_providers_api.py::test_tc018_api_validation | ⏳ 待执行 |
| TC-019 | AC-003-3 | 017/025/026 | test_ai_adapters.py::test_tc019_connection_test_timeout；test_providers_service.py::test_tc019_connection_test_timeout；test_providers_api.py::test_tc019_api_connection_test | ⏳ 待执行 |
| TC-020 | AC-003-4 | 025 | test_providers_service.py::test_tc020_disabled_provider_blocks_models | ⏳ 待执行 |
| TC-021 | AC-003-3 | 017/025/026/028 | test_ai_adapters.py::test_tc021_connection_test_error_classification；test_providers_service.py::test_tc021_connection_test_error_codes；test_providers_api.py::test_tc021_api_connection_test_failure | ⏳ 待执行 |
| TC-022 | AC-003-1 | 025/026 | test_providers_service.py::test_tc022_update_key_blank_keeps；test_providers_api.py::test_tc022_api_patch_key | ⏳ 待执行 |
| TC-023 | AC-004-1 | 027/029 | test_models.py::test_tc023_create_model_and_ranges | ⏳ 待执行 |
| TC-024 | AC-004-2 | 027/029 | test_models.py::test_tc024_duplicate_model_name | ⏳ 待执行 |
| TC-025 | AC-004-3 | 027/040 | test_models.py::test_tc025_default_params_used_and_override_not_persisted | ⏳ 待执行 |
| TC-026 | AC-009-1 | 014/030/031/033 | test_sessions_service.py::test_tc026_create_session_contract / test_tc026_create_session；test_sessions_api.py::test_tc026_api_create_session | ⏳ 待执行 |
| TC-027 | AC-009-2 | 030/031/033 | test_sessions_service.py::test_tc027_list_filters；test_sessions_api.py::test_tc027_api_filters | ⏳ 待执行 |
| TC-028 | AC-009-3 | 030/031/034 | test_sessions_service.py::test_tc028_timeline_order；test_sessions_api.py::test_tc028_api_events_order | ⏳ 待执行 |
| TC-029 | AC-009-4 | 030/031/032/033 | test_sessions_service.py::test_tc029_terminal_state_rejects；test_sessions_api.py::test_tc029_api_complete_idempotent；test_fail_session_hook.py::test_tc029_unhandled_error_marks_failed | ⏳ 待执行 |
| TC-030 | AC-009-5 | 030/031/046 | test_sessions_service.py::test_tc030_delete_cascades；test_sessions_api.py::test_tc030_api_delete | ⏳ 待执行 |
| TC-031 | AC-001-3 | 031/044 | test_sessions_api.py::test_tc031_recent_sessions_limit10；test_entrances_api.py::test_tc031_home_recent_sessions | ⏳ 待执行 |
| TC-032 | AC-006-1 | 035/037 | test_inputs_api.py::test_tc032_append_text_event | ⏳ 待执行 |
| TC-033 | AC-006-2 | 035/037 | test_inputs_api.py::test_tc033_empty_text_rejected | ⏳ 待执行 |
| TC-034 | AC-006-3 | 035/037 | test_inputs_api.py::test_tc034_text_over_limit_rejected | ⏳ 待执行 |
| TC-035 | AC-006-1 | 035 | test_inputs_api.py::test_tc035_updated_at_bumped | ⏳ 待执行 |
| TC-036 | AC-007-1 | 015/036/038 | test_artifacts_service.py::test_tc036_save_upload_success；test_artifacts_api.py::test_tc036_upload_success_and_preview | ⏳ 待执行 |
| TC-037 | AC-007-2 | 036 | test_artifacts_api.py::test_tc037_batch_validation_rejects_all | ⏳ 待执行 |
| TC-038 | AC-007-3 | 015/036/038 | test_artifacts_service.py::test_tc038_duplicate_name_renamed；test_artifacts_api.py::test_tc038_duplicate_names_renamed | ⏳ 待执行 |
| TC-039 | AC-007-2 | 012/036 | test_storage.py::test_tc039_path_traversal_rejected；test_artifacts_api.py::test_tc039_traversal_rejected_via_api | ⏳ 待执行 |
| TC-040 | AC-007-1 | 012/036 | test_storage.py::test_tc040_storage_cleanup_on_failure；test_artifacts_api.py::test_tc040_disk_failure_returns_507 | ⏳ 待执行 |
| TC-041 | AC-005-1 | 016/039/040 | test_ai_gateway.py::test_tc041_success_records_call；test_calls_api.py::test_tc041_api_call_success | ⏳ 待执行 |
| TC-042 | AC-005-2 | 016/017/039 | test_ai_gateway.py::test_tc042_upstream_failure_recorded；test_ai_adapters.py::test_tc042_adapter_error_mapping；test_calls_api.py::test_tc042_api_call_failure | ⏳ 待执行 |
| TC-043 | AC-005-3 | 039 | test_calls_api.py::test_tc043_precondition_rejections_no_record | ⏳ 待执行 |
| TC-044 | AC-005-4 | 034/039/040 | test_calls_api.py::test_tc044_call_event_payload | ⏳ 待执行 |
| TC-045 | AC-005-5 | 016/039/047 | test_ai_gateway.py::test_tc045_retry_then_timeout / test_tc045_cancellation_finalizes_record；test_calls_api.py::test_tc045_api_retry_and_timeout | ⏳ 待执行 |
| TC-046 | AC-010-1 | 042/043 | test_calls_query.py::test_tc046_query_calls_ordering | ⏳ 待执行 |
| TC-047 | AC-010-2 | 042/043 | test_calls_query.py::test_tc047_failed_call_detail | ⏳ 待执行 |
| TC-048 | AC-010-3 | 042/043 | test_calls_query.py::test_tc048_empty_result_not_error | ⏳ 待执行 |
| TC-049 | AC-005-1 | 013/047 | test_startup.py::test_tc049_startup_merges_running_calls / test_tc049_restart_merges_running | ⏳ 待执行 |
| TC-050 | AC-005-2 | 025/039 | test_providers_service.py::test_tc050_credential_decrypt_failure_no_record；test_calls_api.py::test_tc050_api_credential_unavailable | ⏳ 待执行 |
| TC-051 | AC-001-1 | 003/044 | test_entrances.py::test_tc051_entrances_has_six_items；test_entrances_api.py::test_tc051_api_entrances_six | ⏳ 待执行 |
| TC-052 | AC-001-2 | 044 | test_entrances_api.py::test_tc052_spa_fallback_entrance_route | ⏳ 待执行 |
| TC-053 | AC-001-2 | 044 | test_entrances_api.py::test_tc053_unknown_entrance_rejected | ⏳ 待执行 |
| TC-054 | AC-002-1 | 045 | test_entrances_api.py::test_tc054_placeholder_metadata | ⏳ 待执行 |
| TC-055 | AC-002-2 | 045 | test_entrances_api.py::test_tc055_placeholder_has_no_side_effects | ⏳ 待执行 |
| TC-056 | AC-002-3 | 003/045 | test_entrances.py::test_tc056_entrance_status_is_config_driven；test_entrances_api.py::test_tc056_entrance_status_switch | ⏳ 待执行 |
| TC-057 | AC-TECH-1 | 002/014/015/016 | test_config.py::test_tc057_frozen_settings_contract；test_sessions_service.py::test_tc057_frozen_session_signatures；test_artifacts_service.py::test_tc057_frozen_artifact_signature；test_ai_gateway.py::test_tc057_frozen_gateway_signature | ⏳ 待执行 |
| TC-058 | AC-TECH-2 | 007/008/009/010/018 | test_engine.py::test_tc058_engine_creation_both_dialects；test_db_migrations.py::test_tc058_models_match_schema_metadata / test_tc058_migrate_empty_db_to_head | ⏳ 待执行 |
| TC-059 | AC-TECH-2 | 009/010/018 | test_db_migrations.py::test_tc059_constraints_on_test_database | ⏳ 待执行 |
| TC-060 | AC-TECH-3 | 011 | test_api_skeleton.py::test_tc060_error_envelope_and_cursor | ⏳ 待执行 |
| TC-061 | AC-TECH-3 | 011/020 | test_api_skeleton.py::test_tc061_origin_check_rejects_cross_site | ⏳ 待执行 |
| TC-062 | AC-TECH-4 | 041 | test_batch_b_smoke.py::test_tc062_batch_b_minimal_loop | ⏳ 待执行 |
| TC-063 | AC-TECH-6 | 006 | test_redaction.py::test_tc063_logs_and_responses_never_contain_secrets | ⏳ 待执行 |
| TC-064 | AC-TECH-2 | 051/055 | test_db_migrations.py::test_tc064_migration_0006_injection_columns / test_tc064_migration_order_before_knowledge_base | ⏳ 待执行 |
| TC-065 | AC-005-1 | 052 | test_ai_gateway_injection.py::test_tc065_no_injection_preserves_baseline | ⏳ 待执行 |
| TC-066 | AC-005-1 | 052 | test_ai_gateway_injection.py::test_tc066_injection_persisted_and_survives_failure | ⏳ 待执行 |
| TC-067 | AC-010-2 | 052 | test_calls_api.py::test_tc067_knowledge_injection_serialization | ⏳ 待执行 |
| TC-068 | AC-TECH-3 | 053/055 | test_sessions_ai_complete.py::test_tc068_invalid_entries_require_confirmation；test_knowledge_contract.py::test_tc068_preparer_contract | ⏳ 待执行 |
| TC-069 | AC-TECH-3 | 053 | test_sessions_ai_complete.py::test_tc069_confirmed_injection_and_limits | ⏳ 待执行 |
| TC-070 | AC-009-3 / AC-010-2 | 054 | test_sessions_api.py::test_tc070_knowledge_injection_timeline_payload；Vitest KnowledgeInjectionEventCard.test.tsx（标题带 TC-070） | ⏳ 待执行 |
| TC-071 | AC-TECH-2 / AC-TECH-3（RISK-011；无独立功能 AC） | 011 | test_db_error_mapping.py::test_tc071_db_error_mapping_is_dialect_portable | ✅ passed（2026-11-18 13:04:22） |

### 覆盖统计

| 维度 | 结果 |
|------|------|
| 功能 AC 覆盖 | 42/42（100%），每条至少 1 个 TC |
| AC-TECH 覆盖 | 6/6（TC-057 ~ TC-064、TC-068、TC-071 覆盖 1/2/3/4/6；AC-TECH-5 由流程校验覆盖，Q-TV-01 已确认 A） |
| TC 定义与 pytest 落点 | 71/71（100%），每个 TC 至少一个 `test_tcNNN_*` |
| 非 `[no-test]` 任务映射 | 50/50（TASK-TD-002 ~ 017、019 ~ 047、051 ~ 055；见 `tc-map.json`） |
| Critical 风险覆盖 | RISK-001/002/005/010/011/012 各 ≥2 TC（RISK-011 含 TC-064 迁移顺序与 TC-071 方言映射）；RISK-009 由范围约束覆盖 |

## 需求覆盖率报告（Round-Trip）

### Round-Trip 验证步骤

1. 读 `requirements-analysis/raw-requirements.md`：原文只有一句需求 + 6 个入口。
2. 原始需求逐项对照 `requirements-analysis/design.md` / `docs/context.md` 的 US/AC：登录、提供商/模型、统一调用、文本/文件输入、项目上下文、制品、调用记录等基座能力来自后续 answers 确认的扩展，不属于原始一句话，但已纳入本 spec 的 AC。
3. 每条 AC 有 TC：42 条功能 AC + 6 条 AC-TECH 均有映射（AC-TECH-5 走流程）。
4. 每条 TC 有执行结果：当前全部 `待执行`，开发完成后由 `aw verify` 回填。
5. 覆盖率 = 有对应 TC 的需求数 / 总需求数。

### 原始需求 → AC → TC 对照

| 原始需求（raw-requirements.md） | 关联 AC | 关联 TC | 执行结果 | 覆盖状态 |
|--------------------------------|---------|---------|---------|---------|
| 搭建 AI 测试工作台（Web 应用基座） | AC-011-1 ~ 7、AC-001-1 ~ 3、AC-008-1 ~ 3、AC-009-1 ~ 5 | TC-001 ~ TC-016、TC-026 ~ TC-035、TC-051 ~ TC-056 | 待执行 | ⏳ pending |
| 入口：用例库（原「生成测试用例」） | AC-001-1、AC-001-2、AC-002-1 ~ 3 | TC-051 ~ TC-056 | 待执行 | ⏳ pending |
| 入口：分析 bug | AC-001-1、AC-001-2、AC-002-1 ~ 3 | TC-051 ~ TC-056 | 待执行 | ⏳ pending |
| 入口：排查日志 | AC-001-1、AC-001-2、AC-002-1 ~ 3 | TC-051 ~ TC-056 | 待执行 | ⏳ pending |
| 入口：分析 SQL | AC-001-1、AC-001-2、AC-002-1 ~ 3 | TC-051 ~ TC-056 | 待执行 | ⏳ pending |
| 入口：生成回归清单 | AC-001-1、AC-001-2、AC-002-1 ~ 3 | TC-051 ~ TC-056 | 待执行 | ⏳ pending |
| 入口：生成测试报告 | AC-001-1、AC-001-2、AC-002-1 ~ 3 | TC-051 ~ TC-056 | 待执行 | ⏳ pending |
| 扩展（answers 确认）：AI 提供商与模型、统一调用与记录 | AC-003-1 ~ 4、AC-004-1 ~ 3、AC-005-1 ~ 5、AC-010-1 ~ 3 | TC-017 ~ TC-025、TC-041 ~ TC-050 | 待执行 | ⏳ pending |
| 扩展（answers 确认）：文本/文件输入与制品 | AC-006-1 ~ 3、AC-007-1 ~ 3 | TC-032 ~ TC-040 | 待执行 | ⏳ pending |
| 扩展（answers 确认）：单用户登录与访问控制 | AC-011-1 ~ 7 | TC-001 ~ TC-012 | 待执行 | ⏳ pending |
| 扩展（A101 / A102 / A103 B，2026-11-18）：知识库注入留痕、唯一调用入口与 `kbDeleted` | AC-005-1、AC-009-3、AC-010-2、AC-TECH-2、AC-TECH-3 | TC-064 ~ TC-070 | 待执行 | ⏳ pending |
| 技术验收（tech-tasks） | AC-TECH-1 ~ 6 | TC-057 ~ TC-064、TC-068、TC-071（AC-TECH-5 流程） | TC-071 通过，其余待执行 | ⏳ pending |

### 覆盖率汇总

| 指标 | 结果 |
|------|------|
| 原始需求条目覆盖 | 7/7（100%） |
| 功能 AC → TC 覆盖 | 42/42（100%） |
| AC-TECH → TC 覆盖 | 6/6（100%，其中 AC-TECH-5 为流程覆盖） |
| TC 定义 → pytest 落点 | 71/71（100%） |
| TC 执行通过率 | 1/71 已回填通过（TC-071，`aw verify` 2026-11-18 13:04:22）；最近一次 verify 报告另有 23 个 TC 为 passed、尚未回填；其余为 `待执行` |
| 测试问题清单 | 18 项（SEC 5 / DATA 6 / UX 4 / PERF 3），其中 DATA-006 为误报（显示层替换，已按字节复核），其余为待验证风险 |

## 执行结果

> 本表是 TC 结果的唯一来源。当前开发未开始，全部为 `待执行`；开发完成后由 `aw verify` 解析 pytest 报告回填「通过/失败」，只有 pytest 报告里没有、且只能人工执行的 TC 才人工回填。失败原因写在「备注」列，用例下不写状态字段。

| TC ID | 用例标题 | 测试类型 | 执行状态 | 执行时间 | 备注 |
|-------|---------|---------|---------|---------|------|
| TC-001 | 未登录访问受保护资源被拦截 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-002 | 正确口令登录并只存令牌哈希 | 单元 + 集成 | 待执行 | — | 待开发完成 |
| TC-003 | 错误口令统一提示且日志无原文 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-004 | 连续失败 5 次锁定 5 分钟、成功清零 | 集成·服务 | 待执行 | — | 待开发完成 |
| TC-005 | 并发失败计数不丢 | 集成·服务 | 待执行 | — | 待开发完成 |
| TC-006 | 空闲 8 小时失效、请求刷新 lastSeenAt | 集成·服务 | 待执行 | — | 待开发完成 |
| TC-007 | 登出立即吊销令牌 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-008 | Cookie 属性 HttpOnly/SameSite/Secure | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-009 | AW_ADMIN_PASSWORD 缺失或空拒绝启动 | 单元 | 待执行 | — | 待开发完成 |
| TC-010 | HTML 导航 302 并保留站内 next | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-011 | 空闲过期后 API 401 与页面跳转 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-012 | next 只接受站内路径 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-013 | 创建项目与重名 409 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-014 | 编辑项目回显与 updatedAt 刷新 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-015 | 无项目不可创建会话 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-016 | 项目名称与仓库地址逐字段校验 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-017 | 密钥加密落库、掩码展示、响应无密钥 | 单元 + 集成 | 待执行 | — | 待开发完成 |
| TC-018 | 提供商必填与 baseURL 校验 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-019 | 连接测试 10s 超时且无副作用 | 集成·服务 | 待执行 | — | 待开发完成 |
| TC-020 | 停用提供商后模型不可选、历史可查 | 集成·服务 | 待执行 | — | 待开发完成 |
| TC-021 | 连接测试失败分类 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-022 | 空密钥不改、新值重新加密 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-023 | 新增模型与参数范围 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-024 | 同提供商同名模型 409 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-025 | 默认参数生效、本次覆盖不回写 | 集成·服务 | 待执行 | — | 待开发完成 |
| TC-026 | 创建会话、状态进行中、置顶 | 契约 + 集成 | 待执行 | — | 待开发完成 |
| TC-027 | 项目/状态筛选与倒序、游标分页 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-028 | 时间线按发生顺序 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-029 | 完成/失败终态拒绝写入 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-030 | 删除会话级联清理且不影响其他会话 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-031 | 首页最近 10 条会话与空态 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-032 | 提交文本追加 input_text 事件 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-033 | 空或纯空白正文拒绝 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-034 | 超过 200,000 字符拒绝并给出字数 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-035 | 追加事件刷新会话 updated_at | 集成·服务 | 待执行 | — | 待开发完成 |
| TC-036 | 上传成功、事件、元数据与预览下载 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-037 | 白名单/大小/数量整批拒绝 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-038 | 同名自动改名保留两份 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-039 | 路径穿越与符号链接拒绝 | 单元 + 集成 | 待执行 | — | 待开发完成 |
| TC-040 | 磁盘失败 507、无残留与无 DB 行 | 单元 + 集成 | 待执行 | — | 待开发完成 |
| TC-041 | 成功调用返回文本与 callId、写记录与事件 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-042 | 上游失败记录并可读错误 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-043 | 前置拒绝不产生调用记录 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-044 | 时间线与详情展示摘要且无密钥 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-045 | 重试 1 次、超时不重试、取消终结 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-046 | 按会话/项目/时间查询倒序 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-047 | 失败详情含错误与重试次数、无密钥 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-048 | 无匹配返回空列表而非错误 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-049 | 启动归并 running → failed(interrupted) | 集成·服务 | 待执行 | — | 待开发完成 |
| TC-050 | 凭据解密失败 502 且无记录 | 集成·服务/接口 | 待执行 | — | 待开发完成 |
| TC-051 | 6 个入口含名称与用途 | 单元 + 集成 | 待执行 | — | 待开发完成 |
| TC-052 | 入口路由刷新直达（SPA fallback） | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-053 | 未知入口 key 拒绝 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-054 | 占位页说明所属域、状态与返回入口 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-055 | 占位页无副作用 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-056 | 入口 planned/live 由配置驱动 | 单元 + 集成 | 待执行 | — | 待开发完成 |
| TC-057 | 四个冻结签名契约与配置契约 | 契约 | 待执行 | — | 待开发完成 |
| TC-058 | SQLite 空库迁移到 head 且模型一致 | 集成·迁移 | 待执行 | — | 待开发完成 |
| TC-059 | MySQL 关键约束复验 | 集成·迁移 | 待执行 | — | 本地 SQLite 必跑；MySQL 证据见 CI job 2 |
| TC-060 | 错误体、requestId 与游标分页契约 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-061 | Origin/Referer 校验 403 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-062 | 批次 B 最小闭环冒烟 | 集成·冒烟 | 待执行 | — | 待开发完成 |
| TC-063 | 日志、响应与记录中无密钥与口令 | 单元 + 集成 | 待执行 | — | 待开发完成 |
| TC-064 | 迁移 0006 四列与 CHECK，先于 knowledge-base 0007 | 集成·迁移 | 待执行 | — | 待开发完成 |
| TC-065 | injection=None 时记录与事件与扩展前一致 | 集成·服务 | 待执行 | — | 待开发完成 |
| TC-066 | 注入时写四列与事件，失败/超时保留 | 集成·服务 | 待执行 | — | 待开发完成 |
| TC-067 | 序列化 knowledgeInjection 与 kbDeleted | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-068 | 失效未精确确认 409 且无记录/无外部请求 | 集成·接口/契约 | 待执行 | — | 待开发完成 |
| TC-069 | 精确确认后调用；空集 409、超预算 400 | 集成·接口 | 待执行 | — | 待开发完成 |
| TC-070 | 时间线与调用详情展示注入快照 | 集成·接口 + Vitest | 待执行 | — | 待开发完成；UI 渲染由 CI job 3 提供证据 |
| TC-071 | 数据库约束错误映射的方言可移植性 | 集成·接口 | 通过 | 2026-11-18 13:04:22 | `aw verify` 通过（head eef4da4）；源于 CI `mysql-tests` 抓出的双方言差异 |

## 测试问题清单（ISSUE LIST）

> 开发未开始，以下为「待验证风险项」：每项必须由对应 TC 的结果确认或否定，不能提前写成缺陷，也不能当成已通过。

| 编号 | 分类 | 问题描述 | 关联 TC | 验证方式 |
|------|------|---------|---------|---------|
| SEC-001 | 🔴 安全 | 上游错误体或 SDK 异常可能回显 `Authorization`/密钥 | TC-017、TC-042、TC-063 | 断言响应、日志、记录中无原文 |
| SEC-002 | 🔴 安全 | 上传文件名或制品路径穿越、符号链接读到会话目录外 | TC-037、TC-039 | 单元 + 接口构造恶意路径 |
| SEC-003 | 🔴 安全 | 登录绕过、`next` 开放重定向、代理下 IP 识别错误导致锁错人 | TC-001、TC-010、TC-012、TC-061 | 无 Cookie/伪造 next/Origin |
| SEC-004 | 🔴 安全 | 口令、令牌、密钥进入响应、日志或前端存储 | TC-003、TC-008、TC-063 | caplog + 响应扫描 |
| SEC-005 | 🔴 安全 | CSRF：缺失或错误 Origin 的写请求被执行 | TC-061 | 三类 Origin 断言 |
| DATA-001 | 🟡 数据 | 并发失败计数丢更新或 SQLite 写锁泄漏为 500 | TC-005 | `asyncio.gather` 并发 |
| DATA-002 | 🟡 数据 | 删除会话留下文件或行残留、误删其他会话 | TC-030 | 四类行 + 目录核查 |
| DATA-003 | 🟡 数据 | 200,000 字符、10MB、10 个、同名校验边界偏差或静默截断 | TC-034、TC-037、TC-038 | 精确边界值 |
| DATA-004 | 🟡 数据 | 终态会话仍接受写入或标记完成不写事件 | TC-029、TC-035 | 状态流转 + 事件断言 |
| DATA-005 | 🟡 数据 | 注入四列与快照/正文不一致，或失败后留痕被回滚 | TC-064、TC-066 | 列不变量 + CHECK + 失败路径断言 |
| DATA-006 | 🟡 数据 | 误报（显示层替换所致）：曾疑 400 的 `code` 与 `api-spec.md` 不一致。按文件字节复核，实现 `src/workbench/api/errors.py` 的 400 code 与 api-spec 两条 400 行的 code 均为同一 16 字节序列（`hex` 均为 `76616c69646174696f6e5f6572726f72`），完全一致，不存在契约差异 | TC-071、TC-060 | `python3 -c` 读文件字节并打印 `hex()` 比对；不肉眼比对渲染后的文本 |
| UX-001 | 🟢 体验 | 空态与错误态混淆、筛选无结果被当成错误 | TC-027、TC-031、TC-048 | 接口空列表 + Vitest 空态 |
| UX-002 | 🟢 体验 | 锁定倒计时、过期提示与草稿恢复不符设计 | TC-004、TC-011、M-01/M-02 | 人工 + Playwright |
| UX-003 | 🟢 体验 | 调用中可重复提交、失败后提示不可读 | TC-041、M-06 | Vitest + 人工 |
| PERF-001 | 🔵 性能 | 分页上限、游标稳定性、超大列表响应体 | TC-027、TC-028、TC-046、TC-060 | 边界分页断言 |
| PERF-002 | 🔵 性能 | 并发信号量排队计入 latency 或调用中占满连接 | TC-045、TC-049 | 假适配器 + 计数断言 |
| PERF-003 | 🔵 性能 | 注入后正文超过 200,000 字符未拒绝，或预算计算把注入块漏算 | TC-069 | 预算边界 199999/200000/200001 |
| UX-004 | 🟢 体验 | 知识库已删除仍显示为正常引用，误导用户 | TC-067、TC-070 | `kbDeleted` 三态 + 前端文案 |

## 缺陷分级与回归口径

### 缺陷等级

| 等级 | 定义 | 处理时限 | 是否阻塞 verify/close |
|------|------|---------|----------------------|
| D0 阻塞（Blocker） | 认证可绕过、密钥/口令泄露、路径穿越、数据丢失、迁移失败、应用无法启动 | 立即停止当前批次 | 是 |
| D1 严重（Critical） | AC 主路径不满足；TC 失败且无 workaround；双方言仅一种通过 | 批次内修复 | 是 |
| D2 一般（Major） | 异常/边界不满足，有 workaround；UI 状态缺失但不影响核心流程 | 批次内修复，可带条件验收 | 是（对应 TC 必须通过） |
| D3 轻微（Minor） | 文案、间距、非关键视觉偏差 | 记录后修复 | 否，但需用户同意延期 |
| D4 建议（Trivial） | 可读性、注释、优化建议 | 不进缺陷清单 | 否 |

### 回归口径

- 任何修复后必须重跑：全量 pytest（71 个 TC）+ `python3 .aw/aw.py verify`。
- 改动范围 → 必跑用例：
  - 认证/依赖/Cookie/Origin → TC-001 ~ TC-012、TC-060、TC-061。
  - 迁移/模型/约束 → TC-058、TC-059、TC-064，并确认 CI job 2 绿。
  - 上传/存储/删除 → TC-030、TC-036 ~ TC-040。
  - 网关/适配器/重试/启动 → TC-041 ~ TC-045、TC-049、TC-050、TC-062。
  - 知识库注入/序列化/唯一入口 → TC-064 ~ TC-070，并确认知识库 spec（TC-101 起）的契约用例同步通过。
  - 前端组件 → 同一 TC 的 Vitest 用例 + M-01/M-02。
- 偶发失败：按 RISK-004 记为缺陷（附失败输出），不得用重跑掩盖；连续两次失败结果不同也要记录。
- 修复后结果以最新一次 `aw verify` 与 CI 三个 job 为准；旧报告不作为证据。
- 范围变更（新增 AC）必须先补 TC 与用例，再实现；不得先实现后补测试。

## 人工验证清单与产出物

> 这些项无法由 pytest 可信覆盖，必须人工执行并留证。产出物统一放 `specs/ai-test-workbench_20261117184149/test-verification/evidence/manual/`（建议目录结构见下），不提交真实密钥与个人信息。

| 编号 | 项目 | 为什么只能人工 | 执行者 | 通过标准 | 产出物与落点 |
|------|------|---------------|--------|---------|-------------|
| M-01 | UI 视觉与双主题验收（9 条路由：`/login`、`/`、`/entrances/:key`、`/providers`、`/providers/:id/models`、`/projects`、`/sessions`、`/sessions/:id`、`/calls`） | 视觉一致性、暗/亮 token、布局与焦点态无法用接口断言 | 用户（可请 aw-qa 陪同记录） | 与 `interaction-design/docs/design-system.md` 一致；无溢出/遮挡；明暗各一轮无控制台错误 | `evidence/manual/screens/<theme>/<route>.png` + `manual-acceptance.md` 记录表 |
| M-02 | Playwright 回归（复用 interaction-design 的 31 项断言，明/暗各一轮） | 脚本为临时文件、未入库；且不进必过门禁 | 用户 / 可选自动化 | 31/31 PASS，0 console error（按当前实现重跑） | `evidence/manual/playwright/run-<date>.log` + 截图 |
| M-03 | docker compose 启动（TASK-TD-048） | 容器构建、MySQL 服务、迁移后启动无法在 pytest 内验证 | 用户 | `docker compose up` 后健康检查 401 符合预期；首页可登录 | `evidence/manual/deploy.md`（命令、输出、截图） |
| M-04 | 备份与恢复演练（TASK-TD-049） | 依赖真实 MySQL 与文件系统；本期只做一次手工演练 | 用户 | 备份文件可恢复；`alembic_version` 与制品数量核对一致 | 记录写入 `docs/ai-test-workbench/dev-setup.md` 恢复演练段 + 摘要入 `evidence/manual/backup-restore.md` |
| M-05 | HTTPS/TLS 反代下 Secure Cookie 与登录（AC-011-7） | 真实浏览器 + TLS 终止，自动化只能看响应头 | 用户 | Cookie 带 `Secure`；登录/登出正常；HTTP 下不误设 Secure | 浏览器开发者工具截图 `evidence/manual/tls-cookie.png` |
| M-06 | 长调用体验（>120s、最坏 ~240s；RISK-003） | 真实等待与前端 300s 超时、调用中禁用、失败恢复 | 用户 | 调用中不可重复提交；超时后展示可读错误；时间线写入失败事件 | 录屏或步骤记录 `evidence/manual/long-call.md` |
| M-07 | 知识库注入展示（TC-070 的前端部分） | 卡片视觉、`kbDeleted` 文案与信息层级无法由 pytest 断言 | 用户 | pytest 已证明事件 payload、调用详情序列化与 `kbDeleted` 布尔值；CI job 3 的 Vitest 证明卡片渲染与「无注入不渲染」；人工复核暗/亮主题下卡片文案与「知识库已删除」标识可读、不展示正文 | 截图 `evidence/manual/screens/<theme>/session-injection.png` + 记录 |

补充说明：

- **TC-070 的两层证据边界**：pytest（`tests/test_sessions_api.py::test_tc070_knowledge_injection_timeline_payload`）证明事件 payload 字段、`kbDeleted` 三态与详情序列化，结果进入 `aw verify`；Vitest（`KnowledgeInjectionEventCard.test.tsx`，标题带 TC-070）证明卡片渲染、文案与无注入不渲染，只进入 CI job 3 报告，`aw verify` 不读取；视觉与双主题仅由 M-07 人工复核。三者缺一不可，不能用其中一层替代另一层。

- `evidence/manual/` 与 `evidence/verify.json` 同属 spec 的证据区，agent 不修改；人工验收完成后由执行者写入。
- 真机 AI 连通（真实密钥、外网）为可选项：有密钥时执行并记录；无密钥时写「未验证（无可用提供商凭据）」，不得写成通过。
- MySQL 双方言证据来自 CI job 2 的运行记录，不属人工清单；关闭前需附 CI run 链接/日志摘要到 `evidence/manual/ci-runs.md`（Q-TV-02 已确认 A）。公开仓库的截图与日志不得含真实令牌、真实项目名或个人信息。

## CI 与本地验证分工

| 层 | 命令 / job | 是否进 `.aw` 证据 | 证明什么 | 失败后果 |
|----|-----------|------------------|---------|---------|
| 本地 pytest（SQLite） | `python3 .aw/aw.py verify`（或 `pytest`） | 是；71 个 TC 的权威结果 | 功能、接口、契约、SQLite 迁移（含 0006）；不含 MySQL 独有错误码 | verify 红，禁止 close |
| CI job 1 `backend-tests` | `uv sync --frozen` + `aw.py verify` | 否（同一批用例的复跑） | 干净环境可复现 | CI 红 |
| CI job 2 `mysql-tests` | MySQL 8.4 service + `alembic upgrade head` + 同一套 pytest | 否 | 双方言（RISK-011） | CI 红 |
| CI job 3 `frontend-tests` | `npm ci && npm run test -- --run`（Vitest） | 否 | UI 层同一 TC 编号的第二实现 | CI 红；分支保护阻止合并 |
| 人工验收 | M-01 ~ M-06 | 记录写入 `evidence/manual/` | 视觉、部署、备份、TLS、长调用 | 不阻塞 `aw verify`，但阻塞验收与 close 的人工判断 |

明确边界：

- SQLite 绿不等于双方言通过；MySQL 绿以 CI job 2 为准。
- Vitest 绿不等于 `aw verify` 通过；`aw close` 不读取 Vitest。
- Playwright 不进任何必过 job。
- 本地缺 `AW_TEST_DATABASE_URL` 时不允许把 TC-059 整体 skip；TC-059 的通用约束断言必须在 SQLite 上执行并产生报告结果。
- TC-071 是 CI `mysql-tests` job 暴露方言差异后补的回归用例：MySQL 3819/1062/1451/1452 只在真实 MySQL 驱动下出现，本地 SQLite 用例通过不能替代 CI job 2；该条同时说明「本地只跑 SQLite」的局限与第二 job 的必要性。

## 验收清单

关闭前逐项确认：

- [ ] 71 个 TC 在 `## 执行结果` 中都有结果（`通过` / `失败` / `未执行` + 理由），无 `待执行` 遗留。
- [ ] `python3 .aw/aw.py verify` 绿；失败数为 0；71 个 TC 全部由 pytest 报告识别。
- [ ] 功能 AC 42/42、AC-TECH 6/6 在覆盖矩阵中有 TC 或流程说明（AC-TECH-5）。
- [ ] 7 个 🔴 Critical 风险均有对应 TC 且通过；RISK-009 的范围约束无突破（无知识库/仓库集成代码）。
- [ ] CI 三个 job 全绿（`backend-tests`、`mysql-tests`、`frontend-tests`），CI run 记录已归档。
- [ ] core 迁移 head 为 `0006`，且 `0006` 先于 knowledge-base 的 `0007`；TC-064 ~ TC-070 全部通过；跨 spec TC 编号符合约定（core 001 ~ 070 / knowledge-base 101 起 / repo-integration 201 起）。
- [ ] 5 个 `[no-test]` 任务有手工证据：依赖与工具链（TASK-TD-001）、CI（018）、部署（048）、备份（049）、文档（050）。
- [ ] 人工项 M-01 ~ M-06 有产出物与结论；未执行的项明确写「未验证」。
- [ ] 测试问题清单 14 项逐条有结论（确认/否定/转缺陷单）。
- [ ] 代码已提交，`aw.py verify` 与评审对应当前代码指纹。
- [ ] 任何延期项（D3 及以下）已获用户同意并记录在 `open-questions.md` 或审批记录中。

## 下游衔接

- 跨 spec 编号：core 固定使用 TC-001 ~ TC-071；knowledge-base 从 TC-101 起；repo-integration 从 TC-201 起。新增 TC 只能在本段内顺延（core 不新增 TC-072+，除非整体重新编号并同步三份 spec）。
- 开发阶段：`aw-implementer` 按 `technical-design/tasks.md` 分批实现（含批次 D：TASK-TD-051 ~ 055），同时按本文件的「自动化落点」写 `test_tcNNN_*` 用例；不得改本文件的 TC 编号、AC 映射与预期。
- 验证阶段（`MODE=verify`）：`aw.py verify` 产出 `evidence/verify.json` 的 `tcs`，由 aw-qa 回填 `## 执行结果`、`## 测试问题清单` 与 `## 需求覆盖率报告`；pytest 报告里没有的 TC 才允许人工执行后回填。
- 回归：`docs/regression.md` 按 TC 分节维护，后续 spec 复用时按节合并。
- 知识库：本阶段确认后由编排者用 `kb-sync` 将 `docs/regression.md` 提升到 `docs/ai-test-workbench/test-verification/`，`index.md` 由 kb-sync 生成。
