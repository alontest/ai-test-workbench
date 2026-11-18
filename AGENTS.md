# AGENTS.md

<!-- 项目级常驻上下文：构建命令、架构约定、目录规范。≤150 行。 -->

<!-- >>> alonwf (managed) >>> -->
## AlonWorkflow（规格驱动开发流程）

本项目的需求 → 设计 → 开发由 AlonWorkflow 编排。阶段由子代理产出、由用户在对话里确认；`.aw/aw.py` 只为模型不可信、人又不会去查的事背书：测试真跑过且通过、TC 出现在测试报告里、代码已提交、评审之后代码没再变。

- **入口**：新需求用 `aw-start`；继续 / 确认阶段 / 给修改意见用 `aw-next`；评审用 `aw-review`；关闭用 `aw-close`。Claude Code 中是斜杠命令（插件安装时为 `/alon-workflow:aw-start`），Codex 中是同名技能。
- **阶段**：intake → requirements-analysis → interaction-design → tech-arch → tech-design → tech-tasks → test-verification → 开发（按需求类型裁剪，见 `.aw/phases.json`；阶段列表在 `<SPEC_DIR>/spec.json`）。
- **确认**：每个阶段只能由用户在对话里确认，编排者把用户原话记进 `<SPEC_DIR>/approvals.md`。Agent 不得替用户确认，不得修改 `<SPEC_DIR>/evidence/`、`.aw/`，不得使用 `--no-verify`。
- **证据**：`python3 .aw/aw.py verify` 跑 `.aw/config.json` 的 `test` 并读测试报告；`aw.py review run` 由引擎起只读评审 CLI、自己解析裁决并绑定代码指纹（agent 自己写的评审不算；不评审只能由人执行 `review waive <理由>`）；`aw.py close` 要求阶段文件齐全、代码已提交、verify 与评审都对应当前代码、每个 TC 有结果。CI 跑 `python3 .aw/aw.py ci` 从零重跑测试。
- **测试命名**：用例名带 TC 编号（`test_tc001_x` / `TC001_X` / `[Fact(DisplayName = "TC-001 …")]`），否则报告里认不出 TC。
- **上下文纪律**：主会话只做调度，阶段产物由子代理（aw-analyst / aw-ux / aw-architect / aw-qa / aw-implementer / aw-reviewer）生成；主会话不要读 `.aw/phases/`。
- **产物位置**：规格写 `specs/<module>_<timestamp>/<phase-dir>/`；知识库 `docs/<module>/` 由 skill `kb-sync` 在用户确认后同步，子代理不直接写。
- **进度**：`python3 .aw/aw.py status`；单阶段自检：`python3 .aw/aw.py check <SPEC_DIR> --phase <阶段>`。
<!-- <<< alonwf (managed) <<< -->
