# 领域事件（knowledge-base）

> 本文件只追加。条目编号 `DE-C{序号}` 从 1 递增，用过的编号不复用。
> 本期无事件总线：事件以「进程内服务调用 + `session_event` 落库」实现；下列载荷即实际写入/返回的结构，类名一栏是将来引入事件总线时的建议命名，不是现有代码。

### DE-C1 知识库导入成功

- **对应图谱**：未覆盖
- **触发条件**：`KnowledgeImportService.import_files()` 完成文件落盘、解析与单事务提交之后（`knowledge_base` 行 + 条目入库成功）。
- **载荷**：`{kbId, projectId, name, version, entryCount, fileCount, totalByteSize, generatedAt, supersededPrevious: bool}`；不含正文、摘要与字段值。
- **发布域**：knowledge-base
- **订阅方**：无（本期仅返回给 API 调用方）；建议事件类 `KnowledgeBaseImported`，如引入订阅方再加 `KnowledgeBaseImportedHandler`。前端通过 TanStack Query 失效 `["kb"]` 前缀刷新。
- **来源 spec**：knowledge-base_20261117205011（US-012 / AC-012-1）

### DE-C2 知识库版本被取代

- **对应图谱**：未覆盖
- **触发条件**：同名逻辑库再次导入成功，旧行被置为 `status='superseded'`、`current_flag=NULL`、`superseded_by_kb_id=<新 kbId>` 的同一事务内。
- **载荷**：`{projectId, nameKey, previousKbId, previousVersion, newKbId, newVersion}`。
- **发布域**：knowledge-base
- **订阅方**：无；建议事件类 `KnowledgeBaseSuperseded`。读取方按 `current_flag='1'` 自行取当前版本，不依赖事件。
- **来源 spec**：knowledge-base_20261117205011（US-013 / AC-013-4、US-015 / AC-015-2、AC-REQ-24）

### DE-C3 知识库已删除

- **对应图谱**：未覆盖
- **触发条件**：`KnowledgeLifecycleService.delete_logical()` 删除逻辑库全部版本的 DB 事务提交之后；文件清理结果不影响事件。
- **载荷**：`{projectId, nameKey, kbIds: string[], deletedAt}`；不含名称以外的内容字段。
- **发布域**：knowledge-base
- **订阅方**：无（历史 `session_event` / `ai_call_record` 不修改，读取时按 `kbId` 左连接判定 `kbDeleted`）；建议事件类 `KnowledgeBaseDeleted`。
- **来源 spec**：knowledge-base_20261117205011（US-016 / AC-016-1 ~ AC-016-3、AC-REQ-23）

### DE-C4 知识注入留痕

- **对应图谱**：未覆盖
- **触发条件**：core 的 `AiGateway.complete(..., injection=snapshot)` 在插入 `running` 调用记录时，同事务追加 `session_event(type='knowledge_injection')`。本 spec 只产出 `InjectionSnapshot`，写入归 core。
- **载荷**：`{items: [{kbId, kbName, kbVersion, entryCodes[], injectedChars}], promptChars, injectedChars, totalChars, excludedCodes[]}`；只记标识、编号与字符数，**不复制正文**（ADR-111 / BR-C18）。
- **发布域**：knowledge-base（快照）→ workbench-core（写入与发布）；建议事件类 `KnowledgeInjected`，写入点 `AiGateway.complete`，展示点 core 的 calls / 时间线序列化。
- **订阅方**：core 的会话时间线与调用记录读取（按 `kbId` 左连接 `knowledge_base` 计算 `kbDeleted`）。
- **来源 spec**：knowledge-base_20261117205011（US-014 / AC-014-2、AC-014-5、AC-REQ-21）
