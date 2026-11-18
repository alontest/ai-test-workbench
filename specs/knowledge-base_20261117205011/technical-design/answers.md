
## 2026-11-18 11:23:18

用户原话：「A101 A、A102 A、A103 B」。编排者对 A103 的建议被采纳（子代理原推荐 A，改为 B）：

- OQ-ARCH-101 → **A**：由 workbench-core 落地 additive 扩展 —— `ai_call_record` 追加 `knowledge_injection` / `injected_chars` / `prompt_chars` / `total_chars`；`session_event.type` 增加 `knowledge_injection`；core 的 calls 与时间线序列化暴露 `knowledgeInjection` / `kbDeleted`。knowledge-base 只读写，不拥有迁移。
- OQ-ARCH-102 → **A**：`AiGateway.complete` 追加 keyword-only 可选参数 `injection: InjectionSnapshot | None = None`，缺省行为与现状完全一致。
- OQ-ARCH-103 → **B**：**不新增** `/knowledge-injection/calls` 端点；扩展 core 的 `POST /api/v1/sessions/{sessionId}/ai/complete` 请求体，接受知识库引用（`knowledgeRefs`、`confirmInvalidCodes`），由 core 在调用前调用知识库服务做失效重校验与字符预算，入口保持唯一。
- 迁移编号：core 因 A101 新增 revision `0006`，本 spec 的表迁移从 `0007` 起（原 `0006` 作废）。
