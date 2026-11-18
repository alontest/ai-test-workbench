# .aw — AlonWorkflow 运行时（由 alonwf 管理）

| 文件 | 说明 | 可编辑 |
|---|---|---|
| aw.py | 最小引擎：check / verify / review run · waive / close / status / ci（只依赖 Python 3.8+ 标准库） | 否（alonwf update 覆盖） |
| phases.json | 需求类型 → 阶段，每个阶段的必需文件与标记 | 不建议（alonwf update 覆盖） |
| test-presets.json | 测试栈预设：怎么跑、报告在哪、用例名怎么带 TC 编号 | 不建议 |
| config.json | specs_dir / code_paths / exempt_paths / test / review_required / reviewer | 是（改了进指纹，close / CI 打印差异） |
| phases/ | 阶段契约（仅子代理读取） | 否 |
| agents/ | 子代理定义（Codex `codex exec` 退化路径读取） | 否 |
| reference/ | 评审 rubric 与误报清单（aw-reviewer 读取） | 否 |

阶段确认：用户在对话里说「确认」，编排者记进 `<SPEC_DIR>/approvals.md`。证据在 `<SPEC_DIR>/evidence/`，都绑定代码指纹；CI 跑 `python3 .aw/aw.py ci`。
