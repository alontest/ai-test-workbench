# Open Questions — requirements-analysis

## 当前状态（2026-11-17 20:50:31 收窄后）

本 spec 无未决问题。原文件中「知识库需求的 5 项拍板（AMB-014 ~ AMB-018）」与「代码仓库集成的 6 项拍板（AMB-020 ~ AMB-025）」已随需求迁出，原文（含每题选项与用户原话）见：

- 知识库：`specs/knowledge-base_20261117205011/_handoff/from-workbench-core.md` 第 1、2 节
- 仓库集成：`specs/repo-integration_20261117205011/_handoff/from-workbench-core.md` 第 1、2 节

登录相关的三轮拍板（AMB-011 ~ AMB-013、AMB-010）仍属本 spec，结论已回填 `requirements.md` 的「需求澄清」表与 AC，无待确认项：

- AMB-010：文本粘贴单次上限 200,000 字符，超限拒绝、不截断（`answers.md` 2026-11-17 19:04:45「AMB-010 A」）
- AMB-011：管理员口令来自环境变量 `AW_ADMIN_PASSWORD`，缺失拒绝启动，轮换=改环境变量后重启（`answers.md` 2026-11-17 19:58:08）
- AMB-012：登录会话空闲 8 小时失效，无绝对上限（同上）
- AMB-013：同一来源 IP 连续失败 5 次锁 5 分钟，成功登录清零（同上）

## 迁移说明

- 迁出时间：2026-11-17 20:50:31，依据用户原话「我点错了。不是拆2个。另外前边的问题我也没确认呢。一并给我弹窗吧」及弹窗结果「拆 3 个」。
- 本文件不再保留已迁出的 AMB-014 ~ AMB-018、AMB-020 ~ AMB-025 的全文，避免与新 spec 形成两套事实来源；编号与口径以两份 handoff 为准。
