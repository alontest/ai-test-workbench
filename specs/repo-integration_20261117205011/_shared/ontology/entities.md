# Entities

### ENT-C12 代码仓库绑定（CodeRepoBinding）
- **对应图谱**：未覆盖
- **定义**：项目与一个外部代码仓库（云效 Codeup 或 GitHub）之间的只读绑定关系，持有该仓库的访问令牌与最近一次同步状态；是元数据同步、分支选择与按需读文件的入口
- **关键属性**：bindingId、projectId、provider（yunxiao / github）、apiBaseUrl、orgId（云效）/ owner（GitHub）、repoId / repoName、displayName、tokenCiphertext、tokenMasked、tokenExpiresAt（可空）、status（未验证 / 已连接 / 令牌失效 / 已解绑）、lastVerifiedAt、lastSyncAt、lastSyncStatus、createdAt、updatedAt；同一项目下同一提供商 + 同一仓库唯一
- **所属模块**：repo-integration
- **来源 spec**：repo-integration_20261117205011

### ENT-C13 仓库同步记录（RepoSyncRecord）
- **对应图谱**：未覆盖
- **定义**：一次手动同步的执行记录，用于展示上次同步时间、结果与失败原因；不保存令牌与供应商响应原文
- **关键属性**：syncId、bindingId、startedAt、finishedAt、status（成功 / 失败）、repoCount、branchCount、commitCount、errorCategory（鉴权 / 网络 / 限流 / 其他）、errorMessage、createdAt
- **所属模块**：repo-integration
- **来源 spec**：repo-integration_20261117205011

### ENT-C14 仓库元数据快照（RepoMetadataSnapshot）
- **对应图谱**：未覆盖
- **定义**：同步得到的仓库、分支、提交与目录树元数据集合，供选择器与浏览页读取；只含元数据，不含代码文件内容。目录树是否随同步入快照取决于 AMB-026（建议默认：浏览时实时拉取，不入全量快照）
- **关键属性**：snapshotId、bindingId、repoId、kind（仓库 / 分支 / 提交 / 目录树）、ref（分支 / tag / commit）、payload（名称、ID、sha、标题、作者、时间、路径、文件大小）、fetchedAt、truncated（目录树是否被供应商截断）
- **所属模块**：repo-integration
- **来源 spec**：repo-integration_20261117205011

### ENT-C15 仓库文件读取记录（RepoFileReadRecord）
- **对应图谱**：未覆盖
- **定义**：一次按需读取单个文件的审计记录，只记录读取目标与结果，不保存文件正文
- **关键属性**：readId、bindingId、repoId、ref、filePath、byteSize、encoding（text / base64）、status（成功 / 拒绝）、rejectReason（超限 / 二进制或非 UTF-8 / 非法路径）、fetchedAt
- **所属模块**：repo-integration
- **来源 spec**：repo-integration_20261117205011
