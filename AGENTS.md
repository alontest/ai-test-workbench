# AGENTS.md

<!-- 项目级常驻上下文：构建命令、架构约定、目录规范。≤150 行。 -->

## 项目

单用户自托管 AI 测试工作台。后端 Python 3.12 + FastAPI + SQLAlchemy 2.1 + Alembic；前端 React 19 + TS + Vite + React Router 8 + TanStack Query 5 + CSS Modules/Radix。生产 MySQL 8.4，开发/测试 SQLite。`web/dist` 由后端同源托管。

## 常用命令

```bash
uv sync --frozen                    # 安装依赖
uv run pytest -q                    # 后端测试（SQLite）
AW_TEST_DATABASE_URL='mysql+asyncmy://...' uv run pytest   # 双方言
uv run alembic upgrade head         # 迁移
cd web && npm run test -- --run     # 前端测试
cd web && npm run build             # 前端构建
uv run uvicorn workbench.main:create_app --factory --host 127.0.0.1 --port 8000
```

## 架构约定

- **模型出口唯一**：只能走 `AiGateway.complete`。它收口超时 120s、重试、并发、200,000 字符预算与 `AiCallRecord` 生命周期。
- **凭证只由基座持有**：密钥来自环境变量，回显一律掩码，日志一律脱敏。其他域不读密钥、不直连供应商。
- **跨域只走进程内接口**：不跨域读写对方数据表。`projectId` / `sessionId` / `kbId` / `repoBindingId` 都只是 ID 引用。
- **`kbId` 是字符串**：`CHAR(32)` uuid4 hex，core 侧 `kb_id` 已是 `str`。
- **迁移链顺序**：`0001`~`0006` core，`0007` knowledge-base，`0008` repo-integration。不得插队或改历史迁移。

## 双方言纪律

SQLite 绿 ≠ MySQL 绿。CI 有独立 MySQL job。

- 大文本用 `Text().with_variant(MEDIUMTEXT, "mysql")`
- 唯一性靠可空 `current_flag` / `active_flag`（`'1'` / `NULL`），不用布尔列做唯一键
- 新建表直接声明 CHECK，不用 `batch_alter_table` 改历史迁移
- JSON 列用 `sa.JSON`，不建索引

## 仓库不变量（有测试兜底，本地与 CI 都跑）

| 规则 | 保证方式 |
| --- | --- |
| 迁移与模型必须能渲染成 MySQL 8 可执行 DDL，CHECK 不得引用自增列 | `tests/test_mysql_ddl_rules.py` |
| 用例名里的 TC 编号必须登记在 `specs/<spec>/test-verification/tc-map.json` | `tests/test_spec_tc_sync.py` |

## 测试命名

用例名必须带 TC 编号：`test_tc101_rejects_index_without_entries`。TC 编号与 `specs/<spec>/technical-design/docs/test-strategy.md` 一致，不得自创。新增 TC 必须在同一提交登记 tc-map。

## 目录

```
src/workbench/         后端：api/ services/ adapters/ db/ core/ knowledge/ repos/
migrations/versions/   Alembic 迁移
web/src/               前端：app/ features/ components/ lib/ styles/
tests/                 后端测试
specs/<module>_<ts>/   阶段产物（intake → ... → test-verification）
docs/                  交付文档与知识库
```

## 工作方式（pstack）

项目使用 pstack 的写法与流程。这些 skill 已复制到 `.claude/skills/`（已移除 `disable-model-invocation`，模型可自动调用）。

### 强制：第一步必须调 Skill

**任何实现类任务（写代码、改代码、修 bug、重构、写测试），你的第一次工具调用必须是：**

```
Skill(poteto-mode)
```

在它返回之前，不要读文件、不要写代码、不要跑命令。这是硬要求，不是建议。

其余场景按需调用：

| 场景 | 调用 |
| --- | --- |
| 解释架构、走读代码、分层归属 | `Skill(how)` |
| 讨论为什么这样设计、取舍 | `Skill(why)` |
| 修 bug、归类重复错误 | `Skill(correct)` |
| 写文档、注释、提交信息、回复 | `Skill(unslop)` |
| 评估改动影响面、该跑什么测试 | `Skill(blast-radius)` |

### 验证「真的调了」

`AGENTS.md` 里的规则没有强制力，模型可以读、可以复述、也可以不调 skill。唯一可信的证据是工具调用序列。

分派方在 chat 结束后跑：

```bash
python3 scripts/check_poteto.py <pane-id>     # 如 hc:t12
python3 scripts/check_poteto.py --list        # 检查工作区所有 chat
```

退出码 0 = 调用了 `Skill(poteto-mode)`，1 = 没调用，2 = 读不到该 chat。

实测记录（2026-11-20，KB 批次 A~E）：5 个 chat 里只有 1 个调用过，且出现在第 39 次工具调用——说明**光写规则不够，必须事后检查**。

### poteto-mode 的实质规则（不依赖 skill 调用也生效）

以下几条例自 poteto 的核心原则，**无论是否加载了 skill 都必须遵守**：

1. **先说目标与最小改动**。回复开头用一句话复述用户目标，以及满足它的最小改动，然后开始做。
2. **先命名数据形状**。写任何逻辑前，先说清核心类型与数据结构。跨函数边界的改动先定架构。
3. **证明它有效**。任务完成后，用真实产物验证——跑测试、跑构建、看实际输出。不接受「应该可以」「编译通过」当作证据。区分「实测」「推断」「猜测」，标明哪个是哪个。
4. **修根因**。调试时把症状追到系统第一次出错的地方，在那里修。不要加越来越多的检查绕过去。
5. **减法优先**。想加抽象、加层、加参数时，先问能不能删。倾向删除，倾向最小改动。
6. **测试行为而非实现**。断言使用者能观察到的行为，这样内部改动时测试仍然通过，行为破坏时测试会失败。
7. **不要卡在人身上**。可逆的决策自己做，做完给结果让人纠正。只有不可逆的写操作（强推共享分支、部署、删数据、对外发消息）才停下来问。
8. **不做应声虫**。用户征询意见时给出真实判断；不认同就说「这个不值得做」。
9. **回复要短**。短陈述句。先讲对用户有什么变化，再讲怎么做。不用长破折号，不用冒号做连接。
10. **交付前验证清单**：测试跑了没有、构建过了没有、实际输出看了没有。三条都是「是」才算完成。

## 硬约束

- 所有代码改动、构建、git 写操作交给 herdr 里的 coding agent；除非用户明确要求自己动手。
- `specs/` 下的历史阶段产物不修改（保留当时决策痕迹）；废弃命令只在文档顶部加时期说明。
- 改代码前先读现有实现与测试，不凭文档猜文件位置。
