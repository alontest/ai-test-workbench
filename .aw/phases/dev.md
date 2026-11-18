# dev：开发、验证、评审、关闭

> 本文件只描述开发阶段"要什么、产出什么、谁负责、引擎记什么"，不描述怎么调度（调度见 aw-next / aw-review / aw-close）。
>
> - dev 不是 `phases.json` 里的阶段：spec.json 的全部阶段都在 `<SPEC_DIR>/approvals.md` 里有用户确认后，编排者才开始开发。确认是对话里用户亲口说的话，引擎不读 approvals.md。
> - 引擎（`.aw/aw.py`）只为模型不可信、人又不会去查的事背书：测试真跑过且通过、TC 出现在测试报告里、代码已提交、评审之后代码没再变。其余（先红后绿、评审方法、知识库同步）由 agent 定义与 skill 约束。

## 输入

| 输入 | 路径 | 必需 | 用途 |
|---|---|---|---|
| 任务计划 | `<SPEC_DIR>/technical-design/tasks.md` | 是 | `- [ ] TASK-TD-NNN：` 复选框行；`[no-test]` 任务由用户在 tech-tasks 确认 |
| 任务 → TC | `<SPEC_DIR>/test-verification/tc-map.json`（或任务下 `- TC:` 行） | 是 | 每个非 `[no-test]` 任务至少一个 TC，`aw check` 核对 |
| 测试用例 | `<SPEC_DIR>/test-verification/design.md` | 是 | `### TC-NNN` 用例与 `## 执行结果` 表 |
| 本体切片（只读） | `<SPEC_DIR>/ontology-slices/*.md` | 否 | 名称与落点；由 skill `ontology` 生成 |
| 项目配置 | `.aw/config.json` | 是 | `test`（测试栈）、`code_paths`、`exempt_paths`、`review_required`、`reviewer` |

## 产出

| 产出 | 负责 | 说明 |
|---|---|---|
| 业务代码与测试 | aw-implementer | 测试先写、先红后绿；用例名带 TC 编号（写法见 `.aw/test-presets.json` 的 `naming`） |
| `## 执行结果` 表 | aw-qa（MODE=verify） | 自动化 TC 照 verify 报告写；只能人工执行的 TC 真实执行后写 `通过` |

## 引擎记录的证据（`<SPEC_DIR>/evidence/`，都绑定代码指纹）

| 证据 | 命令 | 内容 | close 时要求 |
|---|---|---|---|
| `verify.json` | `python3 .aw/aw.py verify` | 跑 `test` 里的每个栈，读测试报告：通过 / 失败 / 跳过数、报告里每个 TC 的结果、跑前跑后指纹是否一致 | 通过，且指纹等于当前代码 |
| `review.json` | `python3 .aw/aw.py review run`（引擎按 `reviewer` 起只读评审 CLI） / 人执行 `review waive <理由>` | 评审 CLI、版本、模型、prompt 与原始输出的哈希、裁决（阻塞数与发现）；或 waive 的理由 | `review_required` 时：引擎产出且阻塞 0（或有 waive），原始输出没被改，指纹等于当前代码 |
| `closed.json` | `python3 .aw/aw.py close` | 关闭时的指纹与只有人工背书的 TC | — |

close 还要求：所有阶段 `aw check` 通过；业务代码已提交（未跟踪、未暂存、skip-worktree 都算没提交）；每个 TC 在报告里通过，或报告里没有但执行结果表里是 `通过`（列为人工背书）；报告里失败的 TC 不能靠表里写 `通过` 盖掉。

CI 跑 `python3 .aw/aw.py ci`：用基线分支的规则从零重跑测试，复核本分支新关闭 spec 的证据（指纹、verify 声称的 TC 在重跑里也通过、评审来自 review run 或 waive）。这一步不经过模型。规则文件（`.aw/config.json`、`test-presets.json`、`.github/`）改了只打印差异，不拦，合并时由人看。
