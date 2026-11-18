# Interaction Design — Open Questions

## 待用户拍板

无。UXAMB-011 ~ UXAMB-015 已于 2026-11-18 11:12:30 由用户确认（`answers.md`：「RX 全按建议」），本轮无新增阻断项。

## 已确认的交互默认

| 条目 | 结论 | 依据 |
|------|------|------|
| UXAMB-011 仓库绑定面板落位 | 改为**项目详情表单下方的纵向区块**（≤1180px 时项目列表 → 项目详情 → 仓库绑定依次堆叠）；不在 core 两栏之外再切第三栏 | `answers.md` 2026-11-18 11:12:30：「RX 全按建议」；编排者修正为纵向区块，用户接受 |
| UXAMB-012 仓库浏览 | 独立路由 `/projects/:projectId/repos/:bindingId`，面包屑返回 | `answers.md` 2026-11-18 11:12:30：「RX 全按建议」 |
| UXAMB-013 文件查看 | 右侧抽屉 480px（≤768px 全宽），Esc / 遮罩关闭 | `answers.md` 2026-11-18 11:12:30：「RX 全按建议」 |
| UXAMB-014 已解绑呈现 | 留在主列表末尾、整行置灰，令牌「—」，只保留「查看快照 / 重新绑定」 | `answers.md` 2026-11-18 11:12:30：「RX 全按建议」 |
| UXAMB-015 测试结果失效 | 保留上次结果并转灰、标「已失效（时间 · 结果）」；**复用 core 的 `ConnectionTestBadge`**，不另做一套 | `answers.md` 2026-11-18 11:12:30：「RX 全按建议」 |

## 非阻断的设计默认（已落地，若不同意请在确认时提出）

- 状态色映射：已连接 = success，令牌失效 = destructive，未验证 / 已解绑 = muted，即将过期 / 权限不足 / 供应商限流 / 目录树不完整 = warning，同步进行中 = info。
- 同步记录以折叠表呈现，默认收起；「从未同步」不显示空白或错误。
- 成功操作用 Toast，失败不用 Toast（页面横幅 / 区块 ErrorState / 字段错误），避免重复弹错。
- 目录树用文本 `DIR` / `FILE`，不使用 emoji；缩进 20px/级（`--spacing-5`）。
- 令牌字段始终 password 类型，编辑时留空表示不修改。
- 项目列表 / 项目详情表单沿用 core，本 spec 只把「仓库地址」改为自由备注并加来源 hint。

## 上游输入

- 需求分析阶段无未决问题；AMB-026 ~ AMB-031 已由用户于 2026-11-18 10:44:10 全部确认（`requirements-analysis/answers.md`：「全按建议」）。
- 本 spec 无 `ontology-slices/interaction-design.md`（项目尚无 `ontology-work/views/index.json`），状态中文名沿用需求分析的 ENT-C12。
