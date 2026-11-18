# Entities

### ENT-C1 ProjectContext
- **对应图谱**：未覆盖
- **定义**：被测项目的背景信息，是会话的归属单位
- **关键属性**：projectId、name（全局唯一）、repoUrl、techStack、requirementSource、notes、createdAt、updatedAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149

### ENT-C2 ProviderConfig
- **对应图谱**：未覆盖
- **定义**：一个外部 AI 模型服务端点的配置
- **关键属性**：providerId、name、protocol（openai-compatible / anthropic）、baseUrl、apiKeyCiphertext、enabled、createdAt、updatedAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149

### ENT-C3 ModelBinding
- **对应图谱**：未覆盖
- **定义**：提供商下可供调用的具体模型及默认参数
- **关键属性**：modelId、providerId、modelName、displayName、defaultTemperature、defaultMaxTokens、enabled、createdAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149

### ENT-C4 Session
- **对应图谱**：未覆盖
- **定义**：一次分析任务的工作单元，输入、调用与制品的唯一归属
- **关键属性**：sessionId、projectId、entranceKey、title、status（进行中 / 已完成 / 失败）、modelId、createdAt、updatedAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149

### ENT-C5 SessionEvent
- **对应图谱**：未覆盖
- **定义**：会话时间线上的一个事件
- **关键属性**：eventId、sessionId、type（输入 / 调用 / 制品 / 状态变更）、payload、createdAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149

### ENT-C6 Artifact
- **对应图谱**：未覆盖
- **定义**：会话产生的文件级输入或输出
- **关键属性**：artifactId、sessionId、kind、fileName、relativePath（`sessions/<sessionId>/…`）、mimeType、byteSize、createdAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149

### ENT-C7 AiCallRecord
- **对应图谱**：未覆盖
- **定义**：一次经基座发起的模型调用的审计记录
- **关键属性**：callId、sessionId、modelId、promptDigest、status（成功 / 失败 / 超时）、latencyMs、retryCount、errorMessage、createdAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149

### ENT-C8 管理员凭据（AdminCredential）
- **对应图谱**：未覆盖
- **定义**：单用户登录使用的唯一管理员凭据，只保存口令哈希，不保存口令明文
- **关键属性**：credentialId（固定单条）、passwordHash（加盐慢哈希）、updatedAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149

### ENT-C9 登录会话（LoginSession）
- **对应图谱**：未覆盖
- **定义**：一次登录成功后由服务端签发、可吊销的登录会话；用于访问控制，不是分析会话（ENT-C4）
- **关键属性**：loginSessionId、tokenHash（仅存哈希）、createdAt、lastSeenAt、expiresAt（空闲 8 小时失效）、revokedAt（登出或轮换时写入）
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149

> 2026-11-17 20:50:31 收窄：ENT-C10、ENT-C11、ENT-C12、ENT-C13、ENT-C14、ENT-C15 已迁出至 specs/knowledge-base_20261117205011（ENT-C10 ~ C11）与 specs/repo-integration_20261117205011（ENT-C12 ~ C15），原文见对应 `_handoff/from-workbench-core.md`。

### ENT-C10 知识库（KnowledgeBase）
- **对应图谱**：未覆盖
- **定义**：项目级、只读导入的业务知识集合，由 `index.json` 与可选 `.md` 文件构成
- **关键属性**：kbId、projectId、name（同项目内唯一）、version、indexGeneratedAt、entryCount、status（已就绪 / 导入失败 / 已被取代）、totalByteSize、createdAt、updatedAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149
> 已迁出至 specs/knowledge-base_20261117205011（2026-11-17）

### ENT-C11 知识库条目（KnowledgeEntry）
- **对应图谱**：未覆盖
- **定义**：知识库中按编号索引的一条业务知识，是浏览、检索与注入的最小引用单位
- **关键属性**：entryId、kbId、code（编号）、type（术语 / 实体 / 状态 / 业务规则 / 流程 / 接口 / 领域事件 / 其他）、title、summary、body、fields、tables、codePaths、neighbors、freshnessAt、contentDigest
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149
> 已迁出至 specs/knowledge-base_20261117205011（2026-11-17）

### ENT-C12 代码仓库绑定（CodeRepoBinding）
- **对应图谱**：未覆盖
- **定义**：项目与一个外部代码仓库（云效 Codeup 或 GitHub）之间的只读绑定关系，持有该仓库的访问令牌与最近一次同步状态；是元数据同步、分支选择与按需读文件的入口
- **关键属性**：bindingId、projectId、provider（yunxiao / github）、apiBaseUrl、orgId（云效）/ owner（GitHub）、repoId / repoName、displayName、tokenCiphertext、tokenMasked、tokenExpiresAt（可空）、status（未验证 / 已连接 / 令牌失效 / 已解绑）、lastVerifiedAt、lastSyncAt、lastSyncStatus、createdAt、updatedAt；同一项目下同一提供商 + 同一仓库唯一
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149
> 已迁出至 specs/repo-integration_20261117205011（2026-11-17）

### ENT-C13 仓库同步记录（RepoSyncRecord）
- **对应图谱**：未覆盖
- **定义**：一次手动同步的执行记录，用于展示上次同步时间、结果与失败原因；不保存令牌与供应商响应原文
- **关键属性**：syncId、bindingId、startedAt、finishedAt、status（成功 / 失败）、repoCount、branchCount、commitCount、errorCategory（鉴权 / 网络 / 限流 / 其他）、errorMessage、createdAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149
> 已迁出至 specs/repo-integration_20261117205011（2026-11-17）

### ENT-C14 仓库元数据快照（RepoMetadataSnapshot）
- **对应图谱**：未覆盖
- **定义**：同步得到的仓库、分支、提交与目录树元数据集合，供选择器与浏览页读取；只含元数据，不含代码文件内容
- **关键属性**：snapshotId、bindingId、repoId、kind（仓库 / 分支 / 提交 / 目录树）、ref（分支 / tag / commit）、payload（名称、ID、sha、标题、作者、时间、路径、文件大小）、fetchedAt、truncated（目录树是否被供应商截断）
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149
> 已迁出至 specs/repo-integration_20261117205011（2026-11-17）

### ENT-C15 仓库文件读取记录（RepoFileReadRecord）
- **对应图谱**：未覆盖
- **定义**：一次按需读取单个文件的审计记录，只记录读取目标与结果，不保存文件正文
- **关键属性**：readId、bindingId、repoId、ref、filePath、byteSize、encoding（text / base64）、status（成功 / 拒绝）、rejectReason（超限 / 二进制或非 UTF-8 / 非法路径）、fetchedAt
- **所属模块**：workbench-core
- **来源 spec**：ai-test-workbench_20261117184149
> 已迁出至 specs/repo-integration_20261117205011（2026-11-17）
