# 领域事件候选 — workbench-core

> 本文件只追加，旧条目一字不改；修正用新条目并写「取代：<旧编号>」。序号在 `DE-C` 前缀下从 1 递增，不复用。
> 本 spec 未生成 `ontology-slices/tech-design.md`，项目尚无本体参考层，以下候选事件均由 `requirements-analysis/requirements.md` 与 `technical-design/change-spec.md` 推导。

### DE-C1 会话已创建

- **对应图谱**：未覆盖
- **触发条件**：`sessions.create` 成功写入 `analysis_session`（状态 `in_progress`）。
- **载荷**：`{sessionId, projectId, entranceKey, title, modelId, createdAt}`
- **发布域**：`workbench-core`
- **订阅方**：会话所属业务域、后续审计/报表域（本期无订阅方）
- **来源 spec**：`specs/ai-test-workbench_20261117184149`（US-009 / AC-009-1）

### DE-C2 文本输入已提交

- **对应图谱**：未覆盖
- **触发条件**：`sessions.append_event(type="input_text")` 成功，正文非空且 ≤200,000 字符。
- **载荷**：`{sessionId, eventId, title, charCount, createdAt}`
- **发布域**：`workbench-core`
- **订阅方**：会话所属业务域、时间线展示（本期仅时间线）
- **来源 spec**：`specs/ai-test-workbench_20261117184149`（US-006 / AC-006-1/2/3）

### DE-C3 会话制品已保存

- **对应图谱**：未覆盖
- **触发条件**：`artifacts.save` 完成校验、落盘与 DB 写入（含同名自动改名）。
- **载荷**：`{sessionId, artifactId, fileName, byteSize, mimeType, kind, createdAt}`
- **发布域**：`workbench-core`
- **订阅方**：会话所属业务域、仓库/知识库相关域（按 `artifactId` 只读引用）
- **来源 spec**：`specs/ai-test-workbench_20261117184149`（US-007 / AC-007-1/2/3）

### DE-C4 AI 调用已完成

- **对应图谱**：未覆盖
- **触发条件**：`AiGateway.complete` 终结为 `success`。
- **载荷**：`{callId, sessionId, modelId, providerId, latencyMs, retryCount, promptDigest, promptCharCount, finishedAt}`
- **发布域**：`workbench-core`
- **订阅方**：调用方业务域、调用记录查询、后续审计域
- **来源 spec**：`specs/ai-test-workbench_20261117184149`（US-005 / AC-005-1/4/5）

### DE-C5 AI 调用失败

- **对应图谱**：未覆盖
- **触发条件**：`AiGateway.complete` 终结为 `failed` 或 `timeout`（含鉴权、限流、5xx、网络不可达、超时、取消）。
- **载荷**：`{callId, sessionId, modelId, providerId, status, errorCode, errorMessage, latencyMs, retryCount, finishedAt}`
- **发布域**：`workbench-core`
- **订阅方**：调用方业务域、调用记录查询、运维排障
- **来源 spec**：`specs/ai-test-workbench_20261117184149`（US-005 / AC-005-2/5、AC-010-2）

### DE-C6 AI 调用被中断

- **对应图谱**：未覆盖
- **触发条件**：进程启动归并遗留 `running`，或运行期请求被取消后 `finally` 终结为 `failed(interrupted)`。
- **载荷**：`{callId, sessionId, recoveredBy: "startup" | "cancellation", startedAt, finishedAt}`
- **发布域**：`workbench-core`
- **订阅方**：调用记录查询、运维排障（BG-03 失败可见）
- **来源 spec**：`specs/ai-test-workbench_20261117184149`（ADR-010 / `database-schema.md` §7.1）

### DE-C7 会话状态已变更

- **对应图谱**：未覆盖
- **触发条件**：会话由 `in_progress` 变为 `completed`（用户确认）或 `failed`（系统未捕获失败）。
- **载荷**：`{sessionId, from, to, actor, at, reason}`
- **发布域**：`workbench-core`
- **订阅方**：会话所属业务域、时间线展示（本期仅时间线）
- **来源 spec**：`specs/ai-test-workbench_20261117184149`（US-009 / AC-009-4、ADR-012）

### DE-C8 会话已删除

- **对应图谱**：未覆盖
- **触发条件**：`DELETE /api/v1/sessions/{sessionId}` 的文件重命名与 DB 级联删除均完成。
- **载荷**：`{sessionId, projectId, deletedEventCount, deletedArtifactCount, deletedCallCount, deletedAt}`
- **发布域**：`workbench-core`
- **订阅方**：引用过该会话的域（本期无；后续域需按 ID 处理「已删除」）
- **来源 spec**：`specs/ai-test-workbench_20261117184149`（US-009 / AC-009-5）

### DE-C9 知识库注入已留痕

> 2026-11-18 跨 spec 扩展（A101 / A102 / A103 B）新增，编号顺延；DE-C1 ~ DE-C8 原文不改。

- **对应图谱**：未覆盖
- **触发条件**：`AiGateway.complete(..., injection=snapshot)` 插入 `running` 记录时同事务写入 `knowledge_injection` 四列并追加 `session_event(type="knowledge_injection")`。
- **载荷**：`{callId, sessionId, items:[{kbId, kbName, kbVersion, entryCodes, injectedChars, kbDeleted}], promptChars, injectedChars, totalChars, excludedCodes}`
- **发布域**：`workbench-core`
- **订阅方**：调用记录查询、会话时间线、knowledge-base 的历史留痕展示
- **来源 spec**：`specs/ai-test-workbench_20261117184149`（A101 / A102 / ADR-042）
