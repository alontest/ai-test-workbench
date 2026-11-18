# Tech Tasks · Requirements（技术要求与验收口径）

> 阶段：tech-tasks。范围：`workbench-core` 基座（US-001 ~ US-011，AC 42 条，EARS 17 条）。
> 上游已确认：`approvals.md` 末行 `tech-design · 2026-11-18 10:47:44 · 确认`；`docs/architecture-decisions.md`（architecture-locked）、`change-spec.md`、`docs/database-schema.md`、`docs/api-spec.md`、`docs/component-tree.md`、`docs/flowchart.md`；5 项 OQ-TD 均按建议 A 定稿（`answers.md` 2026-11-18 10:44:10「全按建议」）。
> 本文件定义 tech-tasks 阶段自身的技术验收标准（AC-TECH），任务与 TC 映射见 `tasks.md`。

## 1. 范围与前提

- 只实现 workbench-core：登录、入口导航、项目、提供商/模型、会话/事件、文本与文件输入、AI 调用、调用记录、制品、部署。
- 知识库（US-012 ~ US-016）与仓库集成（US-017 ~ US-023）不在本 spec；不新增其表、端点、组件或依赖（`change-spec.md` §7）。
- 冻结签名先行：`sessions.create` / `sessions.append_event` / `artifacts.save` / `AiGateway.complete` 的名称、参数顺序与语义按 `change-spec.md` §3 实现，作为批次 A 的独立任务并被契约测试覆盖；两个新 spec 只调用不修改（ADR-041）。
- 仓库当前无 CI 配置（`.aw/install.json` 的 `ci: null`），本期新增 CI：job 1 跑 `pytest`（SQLite，等价 `aw verify`），job 2 用 MySQL 8.4 service 跑同一套用例（`AW_TEST_DATABASE_URL`）。CI 平台未在仓库中确定，见 `open-questions.md` OQ-TT-01。
- 本地 `python3 .aw/aw.py verify` 只跑 SQLite；「SQLite 绿」不等于双方言通过（RISK-011）。

## 2. AC-TECH（EARS）

**AC-TECH-1（架构锁定落实）**
GIVEN `docs/architecture-decisions.md` 处于 architecture-locked（ADR-001 ~ ADR-028、ADR-041）
WHEN 任一任务开始实现
THEN 只使用已确认的技术栈与目录约定（Python 3.12+/FastAPI/SQLAlchemy 2.1/Alembic/MySQL 8.4+SQLite/React 19+Vite+TanStack Query+Radix），不改冻结签名的名称、参数顺序与返回语义，不新增未经 ADR 记录的依赖；违反时按 `UPSTREAM: tech-arch` 退回，不在本阶段自行改口径。

**AC-TECH-2（数据模型与双方言迁移）**
GIVEN `docs/database-schema.md` 的 10 张表（admin_credential、login_session、login_attempt、project_context、provider_config、model_binding、analysis_session、session_event、artifact、ai_call_record）
WHEN 从空库执行 Alembic 迁移到 head
THEN 每张表的字段类型、空值、默认值、CHECK、唯一约束、索引、外键与级联动作与文档一致；SQLite（aiosqlite）与 MySQL 8.4 均升级成功且关键约束（唯一、CHECK、级联、大小写归一）在两方言均通过用例；迁移拆为 0001 ~ 0005 五个 revision。

**AC-TECH-3（HTTP 契约一致性）**
GIVEN `docs/api-spec.md` 的 30 个端点
WHEN 客户端按文档请求
THEN 路径、方法、请求体、成功响应字段、错误码与 HTTP 状态、`limit`+`cursor` 分页、`aw_session` Cookie 属性与 `{code, message, details[], requestId}` 错误体均与文档一致；除 `POST /api/v1/auth/login` 外均受 `require_session` 保护；所有非安全方法校验 Origin。

**AC-TECH-4（文件清单与批次可独立验收）**
GIVEN `docs/file-structure.md` 的创建顺序与 `tasks.md` 的批次划分
WHEN 完成批次 A 与批次 B
THEN 服务可独立启动，并跑通「登录 → 建项目 → 配提供商/模型 → 建会话 → 贴文本 → 发起调用」最小闭环；批次 C 的调用记录筛选、六入口占位页、部署工件不是批次 B 的前置。

**AC-TECH-5（任务粒度与可执行性）**
GIVEN `tasks.md`
WHEN 评审任务
THEN 每个任务以 `- [ ] TASK-TD-NNN：` 开头，写明具体文件路径、依赖、对应 AC 与 TC 编号（不需要测试的写明 `[no-test]` 与免测理由），复杂度只取 XS/S/M（≤2–3 天），无 L/XL；批次间依赖显式声明。

**AC-TECH-6（Critical 风险与应急预案）**
GIVEN `technical-design/design.md` 风险登记表中的 7 个 🔴 Critical（RISK-001/002/005/009/010/011/012）
WHEN 实现与验收
THEN 每个风险至少有一个可执行 TC 或明确的范围约束与之对应，并在 `tasks.md` 的风险对照表中给出应急预案落点：RISK-001→TC-063，RISK-002→TC-021/TC-042/TC-045，RISK-005→TC-039/TC-040，RISK-009→范围表（本文件 §1），RISK-010→TC-001/TC-008/TC-010/TC-061，RISK-011→TC-058/TC-059，RISK-012→TC-003/TC-004/TC-005/TC-008。

## 3. 关键约定（实现时必须遵守）

- 时间：应用层写 UTC naive；禁止 `NOW()` / `CURRENT_TIMESTAMP`；时间比较只在应用层。
- ID：自增整数，进程内 `int`，API JSON number（OQ-TD-01 A）。
- 唯一性：`name_key` / `model_name_key` / `file_name_key` 存 `casefold()`，列级 `utf8mb4_bin`。
- 删除：只删整个会话；项目/提供商/模型无删除接口，只停用（OQ-TD-02 A）；会话删除先文件进 `.trash` 再删库。
- 快照：`ai_call_record` 冗余 `model_name_snapshot` / `display_name_snapshot` / `provider_name_snapshot` / `protocol_snapshot`（OQ-TD-03 A）。
- 制品：磁盘名 `<uuid4hex>.<ext>`，原名只存库（OQ-TD-04 A）；读取做解析后包含校验并拒绝符号链接。
- 调用：网关失败映射上游 5xx/鉴权/限流/不可达/参数错误 → 502，120s 无响应 → 504 且 `status=timeout`（OQ-TD-05 A）；仅网络错误与 5xx 重试 1 次。
- 常量：200,000 字符、10MB、10 个、120s、10s、8h、5 次/5 分钟集中 `core/constants.py` / `config.py`，不散写魔法数字。
- 秘密：口令、哈希、令牌、API 密钥原文不得进入响应、日志、AiCallRecord、前端可读存储。
- UI：只消费 `interaction-design` 的 Design Tokens（`web/src/styles/tokens.css`），不新增 token，不引入带主题组件库。

## 4. 交付物

| 文件 | 内容 |
|------|------|
| `requirements.md`（本文件） | AC-TECH 与实现约定 |
| `tasks.md` | 50 个任务、批次、依赖、TC↔AC 映射、估点摘要 |
| `docs/file-structure.md` | 目录树、文件职责、创建顺序 |
| `docs/context.md` | 交给 test-verification 的上下文 |
| `docs/dev-setup.md` | 本地环境、命令、环境变量 |

> tech-tasks 未另写 `change-spec.md`：`technical-design/change-spec.md` 是 tech-design 已确认产物，按「不改动上游」保留原文；实施层面的批次顺序、CI、无测试任务与差异说明写在 `tasks.md` 的「任务分组」「估点摘要」与本文件 §1。

## 5. 状态

pending（等待用户在对话中确认 tech-tasks；确认前不进入 test-verification）。
