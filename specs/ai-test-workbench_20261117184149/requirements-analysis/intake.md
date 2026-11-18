# Intake

## 需求类型

🆕 新产品

判定依据：仓库只有 bootstrap 提交（`b29b8fd`），`src/workbench/__init__.py` 仅声明包入口与版本号，`tests/conftest.py` 只有注释，无任何业务实现、无知识库文档（`docs/` 不存在）、无历史 spec。需求是整体搭建一个新工作台，属于全新建库场景。

## 变更性质

🆕 全新模块

首次建立 `ai-test-workbench` 的知识库与规格，没有可增量修改的底稿。

## 交付形态

**Web 应用**（浏览器访问的 Web 前后端；非桌面端、非纯 CLI）。依据：`answers.md` 用户原话「3.交付web应用」。后续技术选型按「Web 前端 + 服务端」进行，界面产物作用于浏览器端。

## 执行路径

本 spec 的分析范围仅限首个域 `workbench-core`（见下节），其余 4 个域各自单独发起 `aw-start`，不纳入本 spec 的用户故事与流程图。

- 需求分析：`market-research` → `competitor-analysis` → `priority-matrix` → `feature-spec` → `requirements-clarify` → `user-story-writer` → `flowchart-generator`（新产品走完整 7 步，素材以 `workbench-core` 域为界）
- 交互设计：执行（`SCOPE` ui=yes，Web 界面上的入口编排与分析工作区需要一个承载界面）
- 技术方案：`tech-stack-advisor` → `risk-analysis` → `architecture-confirm` → `api-design` → `database-design` → `component-breakdown` → `file-structure-generator` → `task-breakdown`
- 测试验证：`test-case-generator` → `auto-test-runner`

## 本 spec 范围

依据：`answers.md` 用户原话「4,按照建议首个域为 workbench-core」，本 spec（module `ai-test-workbench`）作为该域的起点。

在范围内（`workbench-core` 域，域地图中已定义的核心职责）：

- 6 个入口的导航与任务编排（生成测试用例、分析 bug、排查日志、分析 SQL、生成回归清单、生成测试报告 —— 入口只做跳转与任务发起，具体业务能力属其他域）
- AI 模型接入（提供商/模型/密钥管理与统一调用入口 `ai.complete`）
- 输入采集（文本粘贴、文件上传、项目上下文）
- 分析会话与制品记录、落盘（Session、Artifact、AiCallRecord、ProjectContext）

不在范围内（各自单独 `aw-start`）：

- `test-case`：用例生成与用例台账（记录、筛选、回放）
- `diagnosis`：Bug 分析、日志排查、SQL 分析的诊断模型与结论
- `regression-list`：回归清单生成
- `test-report`：测试报告生成

## 上下文扫描

- 相关模块：`ai-test-workbench` 在 `docs/` 下不存在（`docs/` 目录尚未创建）
- 历史 spec：`specs/` 下无其他记录（仅本 spec）
- 已有 docs：无；无 `docs/_shared/domain-map.md`；无 `ontology-work/views/` 本体参考层，因此没有本体切片
- 代码现状：`src/workbench/__init__.py`（仅 `__version__`）、`tests/conftest.py`（仅注释）；`pyproject.toml` 声明包名 `ai-test-workbench`、Python >=3.10、dev 依赖 `pytest>=8.0`、无运行时依赖
- README 补充定位：「记录、筛选、回放一批 AI 测试用例」，说明用例台账（记录/筛选/回放）是本产品自身的一部分，不只是 6 个入口的集合
- 知识库状态：首次建立（用户确认 intake 后由 `kb-sync` 同步）

## 类型与变更性质组合

🆕 新产品 × 🆕 全新模块 → 走全部 7 个阶段，知识库首次建立；不涉及「推翻旧 ADR」的写法。

## 域复杂度评估

多域：是（项目级拆分；本 spec 只覆盖首个域 `workbench-core`，按单域推进）

理由：6 个入口对应 6 类互不相同的核心实体与制品（测试用例 TestCase、缺陷/诊断会话、日志、SQL 语句与执行计划、回归清单、测试报告），存在明显的数据所有权边界；按入口展开后的独立功能点预估超过 30 个，满足 skill `domain-splitter` 的拆分触发条件（≥3 个明显不同的业务实体、多模块平台、任务量 >20 功能点）。

按「高内聚、单一所有权、不超过 8 个域」拆为 5 个域，详细域地图见 `_shared/domain-map.md`：

| 域名称 | module-name | 类型 | 核心职责 |
|---|---|---|---|
| 工作台基座 | `workbench-core` | 通用域 | 入口编排、AI 模型接入、输入采集、会话与制品记录 |
| 用例域 | `test-case` | 核心域 | 生成测试用例 + 用例台账（记录、筛选、回放） |
| 诊断域 | `diagnosis` | 核心域 | Bug 分析、日志排查、SQL 分析共用「输入制品 → AI 诊断」会话模型 |
| 回归清单域 | `regression-list` | 支撑域 | 按变更范围从用例库生成回归清单 |
| 测试报告域 | `test-report` | 支撑域 | 汇总清单与执行结果生成测试报告 |

不把 Bug 分析 / 日志排查 / SQL 分析拆成 3 个域：实际工作流中三者互相取材（排查 Bug 时需要看日志和 SQL），拆开会制造最频繁的跨域调用；三者共享「诊断会话 + 结论」模型，差异在输入制品解析。

## 推进约定

1. `workbench-core`（P0）— 本 spec 的范围；其余域都依赖 AI 接入与会话/制品记录
2. `test-case`（P0）— 回归清单与报告的数据源
3. `diagnosis`（P0）— 与 `test-case` 无依赖冲突，可并行
4. `regression-list`（P1）— 依赖 `test-case` 与 `diagnosis`
5. `test-report`（P1）— 依赖前三者

首个域确认后，其余每个域仍由用户单独发起一次 `aw-start`，使用域地图中的 module-name。本 spec 完成后新增的制品与接口约定，作为后续域的输入。

## 已确认（依据 `requirements-analysis/answers.md`）

| 事项 | 结论 | 依据（用户原话） |
|---|---|---|
| 交付形态 | Web 应用（浏览器访问的 Web 前后端） | 「3.交付web应用」 |
| 首个域 | `workbench-core`；本 spec 作为该域的起点 | 「4,按照建议首个域为 workbench-core」；「本 spec 作为该域起点」为编排者对该答复的解读 |
| 5 域拆分与推进顺序 | 按前述建议保留，`workbench-core` 排第一 | 同上答复中的「按照建议」 |

修订（2026-11-17 20:33:31，已迁出）：原计划把项目上下文修订为「人工填写 + 绑定云效 / GitHub 仓库、按 API 读取元数据与按需读取单个文件」；该需求已于 2026-11-17 20:50:31 随仓库集成整体迁出至 `specs/repo-integration_20261117205011`（US-017 ~ US-023）。本 spec 的项目上下文只保留人工填写字段（项目名、仓库地址文本、技术栈、需求来源、备注）。

修订（2026-11-17 20:50:31）：知识库（US-012 ~ US-016）迁出至 `specs/knowledge-base_20261117205011`；本 spec 范围收窄为纯 `workbench-core` 基座（见 `migration-to-specs.md`）。

修订（2026-11-17 20:12:28）：六入口之一「生成测试用例」更名为「用例库」，生成用例能力作为该入口内部功能，不作为独立入口名；其余五个入口名称不变（详见 `requirements.md` AMB-019）。本文件中上文出现「生成测试用例」之处以该修订为准；`raw-requirements.md` 保留原始需求原文。

## 待确认

无。两项原待定内容已由用户答复，本文件已按其结论收窄范围；如果「本 spec = `workbench-core` 域起点」与你的本意不符，请在确认 intake 时指出。

SCOPE: ui=yes api=yes data=yes
