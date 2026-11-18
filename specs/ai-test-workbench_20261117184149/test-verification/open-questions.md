# Open Questions — test-verification

> 状态：3 项均已确认（2026-11-18 11:23:18，用户原话「TV 全 A」，见 `answers.md`）。以下保留选项与建议值作为决策记录，不再等待拍板；执行一律按已确认的 A 方案。

## Q-TV-01：AC-TECH-5（任务粒度与可执行性）的覆盖口径 —— 已确认 A

- 确认：2026-11-18 11:23:18，用户原话「TV 全 A」（`answers.md`）。结论：按 A 执行，AC-TECH-5 走流程覆盖，不新增 TC-064。

- 背景：`technical-design/requirements.md` 的 AC-TECH-5 要求 `tasks.md` 中每个任务格式合规（文件路径、依赖、AC/TC、`[no-test]` 理由、复杂度 XS/S/M、批次依赖）。这是任务文档的静态格式要求，不是运行时行为；`tasks.md` 的 TC 映射里 TC-057 ~ TC-064、TC-068 覆盖 AC-TECH-1/2/3/4/6，没有 TC 对应 AC-TECH-5。
- 选项：
  - A（建议）：按流程覆盖处理——由 `python3 .aw/aw.py check <SPEC_DIR> --phase tech-tasks` 已通过 + 任务结构评审证明；覆盖矩阵标注「流程覆盖」，不计为覆盖缺口，不新增 TC-064。
  - B：新增 TC-064，由 pytest 解析 `tasks.md` 格式并断言；与「不新增 TC-064+」的既定口径冲突，且需 `aw close` 为该 TC 提供结果。
  - C：把 AC-TECH-5 标记为 ⚠️ not_covered，接受 6 条 AC-TECH 中 1 条无 TC。
- 确认结果：A（2026-11-18 11:23:18，用户原话「TV 全 A」，见 `answers.md`）。

## Q-TV-02：人工验收的执行者与证据落点 —— 已确认 A

- 背景：M-01 ~ M-06（视觉双主题、Playwright、compose 部署、备份恢复、TLS Cookie、长调用体验）无法由 pytest 可信覆盖，需要人工执行并留证；本 spec 目前没有 `evidence/` 目录。
- 选项：
  - A（建议）：由用户在验收环节执行；产出物统一放 `specs/ai-test-workbench_20261117184149/test-verification/evidence/manual/`（`screens/`、`playwright/`、`manual-acceptance.md`、`ci-runs.md`），不提交真实密钥与个人信息；备份恢复的正式记录同时写入 `docs/ai-test-workbench/dev-setup.md`（TASK-TD-049 要求）。
  - B：产出物放 `docs/ai-test-workbench/test-verification/evidence/`，随知识库同步进仓库文档；截图体积与隐私风险更大。
  - C：只写 `manual-acceptance.md` 文字结论，不保存截图/日志。
- 确认结果：A（2026-11-18 11:23:18，用户原话「TV 全 A」，见 `answers.md`）。附加约束：仓库为公开仓库，截图与日志不得含真实令牌、真实项目名或个人信息。CI 三个 job 的 run 链接与失败摘要写入 `evidence/manual/ci-runs.md`，`aw close` 仍只读 pytest 结果。
- 影响：决定 `kb-sync` 是否提升截图与演练记录，以及关闭前人工证据是否可复核。

## Q-TV-03：Playwright 脚本是否入库 —— 已确认 A

- 确认：2026-11-18 11:23:18，用户原话「TV 全 A」（`answers.md`）。结论：不入库，只保存运行日志与截图；开发期若需 E2E 另行立项。

- 背景：interaction-design 的 31 项断言脚本为临时文件、未入库（`design.md` 已注明）；本阶段把它列为可选人工回归（M-02），不进必过门禁。
- 选项：
  - A（建议）：不入库，只保存运行日志与截图（`evidence/manual/playwright/`）；维护成本低，与历来口径一致。
  - B：入库到 `web/e2e/` 并在 CI 增加非必过 job；需新增 Playwright 依赖与浏览器安装步骤，超出 TASK-TD-001 的依赖清单，需补 ADR。
- 确认结果：A（2026-11-18 11:23:18，用户原话「TV 全 A」，见 `answers.md`）。
- 影响：若改选 B，需要新增依赖、CI job 与任务（不在当前 55 个任务内），并更新 `technical-design` 的依赖清单。
