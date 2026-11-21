# File Structure — repo-integration

> 阶段：tech-design（补充产出：目录结构与文件职责）。依据 `technical-design/change-spec.md` §1、`docs/component-tree.md`、`docs/api-spec.md`、`docs/database-schema.md`。
> 仓库基线：core 已建立 `src/workbench/` 与 `web/` 骨架（迁移到 `0006`，knowledge-base 交付 `0007`）；本 spec 只追加仓库集成模块文件，并改动 9 个接入点（见 §4）。测试目录沿用 `tests/`（pytest `pythonpath=["src"]`）。

## 1. 后端目录

```text
migrations/
  versions/
    0007_knowledge_base.py            # knowledge-base 交付（前置，本 spec 不改）
    0008_repo_integration.py          # 本 spec：4 张表，down_revision="0007"

src/workbench/
  repos/                              # 纯逻辑 + 出站适配：不依赖 FastAPI
    __init__.py                       # 导出协议、DTO、常量
    constants.py                      # 10 个契约常量 + REPO_SYNC_MAX_PAGES
    types.py                          # DTO / 枚举 / ProviderError
    errors.py                         # RepoDomainError 族（固定码，不带原文）
    validation.py                     # repoIdentifier / path / ref / apiBaseUrl / search
    crypto.py                         # 仓库令牌加密/解密/掩码（独立密钥）
    cursor.py                         # 游标编码、签名与指纹校验
    ssrf.py                           # 公网 https origin 校验
    redaction.py                      # 供应商异常脱敏
    providers/
      __init__.py                     # build_provider() 注册表
      base.py                         # RepoProvider 协议 + BaseProvider + 错误映射 + 响应头上限
      github.py                       # GitHubProvider（6 方法）
      yunxiao.py                      # YunxiaoProvider（6 方法）
  db/
    models/
      repo_binding.py                 # RepoBinding ORM
      repo_sync_record.py             # RepoSyncRecord ORM
      repo_metadata_snapshot.py       # RepoMetadataSnapshot ORM
      repo_file_read_record.py        # RepoFileReadRecord ORM
      __init__.py                     # 导入四个新模型（修改）
    repositories/
      repos.py                        # RepoRepository（claim、快照覆盖、记录、baseline）
  services/repos/
    __init__.py
    binding_service.py                # RepoBindingService
    connectivity_service.py           # RepoConnectivityService
    sync_service.py                   # RepoSyncService
    browse_service.py                 # RepoBrowseService
    file_service.py                   # RepoFileService
    serializers.py                    # ORM → API camelCase DTO
    registration.py                   # install_repo_services(app)
  api/
    schemas/
      repo.py                         # 请求/响应 Pydantic 模型
    v1/
      repo_bindings.py                # 端点 1~9
      repo_browse.py                  # 端点 10~15
      router.py                       # 修改：挂载两个 router

tests/
  test_repo_config.py                 # TC-248
  test_repo_validation.py             # TC-202 / TC-206 / TC-239
  test_repo_crypto.py                 # TC-201 / TC-246
  test_repo_cursor.py                 # TC-232
  test_repo_provider_github.py        # TC-208 ~ TC-215 / TC-224 / TC-230 / TC-231
  test_repo_provider_yunxiao.py       # TC-208 ~ TC-215 / TC-224 / TC-230 / TC-231
  test_repo_binding_api.py            # TC-201 ~ TC-207
  test_repo_connectivity_api.py       # TC-208 ~ TC-215
  test_repo_sync_service.py           # TC-216 ~ TC-223
  test_repo_sync_api.py               # TC-216 / TC-219 / TC-220 / TC-222
  test_repo_browse_api.py             # TC-224 ~ TC-234
  test_repo_file_api.py               # TC-235 ~ TC-241
  test_repo_lifecycle_api.py          # TC-227 / TC-242 ~ TC-244
  test_repo_security_logs.py          # TC-241 / TC-246
  test_repo_migrations.py             # TC-247
  test_repo_api_contract.py           # TC-245 / TC-249
```

### 文件职责要点

| 文件 | 职责 | 不做什么 |
|------|------|---------|
| `repos/types.py` | 归一化 DTO、枚举、`ProviderError` | 不含供应商参数、不读环境变量 |
| `repos/validation.py` | 仓库标识、路径、ref、域名、检索词校验 | 不发请求、不碰 DB |
| `repos/crypto.py` | 仓库令牌加密/解密/掩码 | 不回落 core 模型密钥；不记录明文 |
| `repos/cursor.py` | 不透明游标与 HMAC 校验 | 不信任客户端页码；不跨绑定复用 |
| `repos/ssrf.py` | 公网 https origin 校验与 DNS 解析 | 不跟随重定向、不访问内网 |
| `providers/base.py` | 共用 `httpx.AsyncClient`、状态码/响应头先于 body、错误映射、5 MiB/1 MiB 上限 | 不拼业务 URL、不写 DB |
| `providers/github.py` | GitHub 六方法与分页/限流/过期头 | 不暴露 owner/repo 之外的供应商参数 |
| `providers/yunxiao.py` | 云效六方法与 `x-*` 分页 | 不假设限流数值；不猜地域域名 |
| `db/repositories/repos.py` | 绑定/记录/快照读写、原子 claim、单事务替换 | 不做供应商请求；不加密解密 |
| `services/repos/sync_service.py` | 拉全量 → 单事务覆盖 → 记录；失败保留 | 不在事务内做网络 IO |
| `services/repos/browse_service.py` | 实时浏览、分页游标、truncated/hasMore、baseline | 不读快照作为浏览数据源 |
| `services/repos/file_service.py` | 前置校验、大小/编码、审计 | 不落盘、不写会话/AiCallRecord |
| `api/v1/repo_*.py` | 参数校验、错误映射、`limit`+`cursor` | 不承载业务规则（在服务层） |

## 2. 前端目录（`web/src/features/repos/`）

```text
web/src/features/repos/
  index.ts                      # 导出页面、挂载面板、routes
  routes.tsx                    # 1 条浏览路由（在 AuthGate 内）
  api/
    types.ts                    # 与 api-spec 对齐的 TS 类型
    client.ts                   # 15 个端点封装
    keys.ts                     # TanStack Query key 工厂
  hooks/
    useRepoBindings.ts
    useRepoBinding.ts
    useCreateRepoBinding.ts
    useUpdateRepoToken.ts
    useTestRepoConnection.ts
    useSyncRepo.ts
    useSyncRecords.ts
    useUnbindRepo.ts
    useRepositories.ts
    useBranches.ts
    useCommits.ts
    useRepoTree.ts
    useRepoFile.ts
    useRepoBaseline.ts
  pages/
    RepoBrowsePage.tsx
  components/
    RepoBindingPanel.tsx
    RepoBindingList.tsx
    RepoBindingRow.tsx
    RepoStatusBadge.tsx
    RepoBindingForm.tsx
    ProviderSegmented.tsx
    TokenField.tsx
    RepoPermissionHint.tsx
    TokenExpiryHint.tsx
    TokenInvalidBanner.tsx
    SyncControl.tsx
    SyncRecordTable.tsx
    UpdateTokenForm.tsx
    RevokedBindingRow.tsx
    RepoPicker.tsx
    BranchPicker.tsx
    RepoBaselineStrip.tsx
    CommitList.tsx
    CommitRow.tsx
    RepoTree.tsx
    TreeNode.tsx
    TreeTruncatedNote.tsx
    FileViewerDrawer.tsx
    UnbindDialog.tsx
    RepoEmptyUnsynced.tsx
    RepoBrowseHeader.tsx
    RepoBreadcrumb.tsx
    RevokedNotice.tsx
```

样式：每个组件配同名 `*.module.css`（CSS Modules，复用 core token 变量）；只在需要布局时新增，不定义新变量。

## 3. 数据与文件落盘布局

```text
数据库（MySQL 8.4 / SQLite）
  repo_binding               # 绑定（含密文，永不出 DTO）
  repo_sync_record           # 同步尝试
  repo_metadata_snapshot     # 基线元数据（仓库/分支/提交）
  repo_file_read_record      # 读取审计（不存正文）

$AW_DATA_DIR/
  sessions/<sessionId>/...   # core 制品（不改）
  # 本 spec 不新增任何落盘目录；文件内容不写磁盘
```

## 4. 对既有文件的改动点

| 文件 | 改动 |
|------|------|
| `src/workbench/config.py` | 新增 `repo_token_key`（`AW_REPO_TOKEN_KEY`）与 32 字节 base64 校验 |
| `src/workbench/startup.py` | 启动自检追加密钥与 Alembic head（含 `0008`） |
| `src/workbench/main.py` | `create_app()` 调 `install_repo_services(app)` |
| `src/workbench/api/v1/router.py` | 注册 `repo_bindings` / `repo_browse` 两个 router |
| `src/workbench/db/models/__init__.py` | 导入四个新模型 |
| `pyproject.toml` | `httpx>=0.28,<0.29` 从 dev 组提升为运行时依赖（版本不变） |
| `web/src/router.tsx` | 追加 `/projects/:projectId/repos/:bindingId` |
| `web/src/app/AppShell.tsx` | 「基座管理」分组追加「仓库浏览」入口 |
| `web/src/features/projects/ProjectsPage.tsx` | 渲染 `<RepoBindingPanel projectId={...} />`（`data-mount="repo-binding-panel"`） |
| `web/src/features/providers/ConnectionTestBadge.tsx` | 扩展 `permission-denied` / `stale` |
| `web/src/features/projects/ProjectForm.tsx` | 「仓库地址」hint 改为自由备注（AMB-030） |
| `web/src/styles/tokens.css` | 追加 `--color-overlay` / `--spacing-5` / `--repo-drawer-width` |

## 5. 创建顺序（供 tech-tasks 拆分）

1. `repos/constants.py`、`types.py`、`errors.py`（无依赖）
2. `repos/validation.py`、`crypto.py`、`cursor.py`、`ssrf.py`、`redaction.py`（依赖 1，可并行）
3. `db/models/repo_*.py`、`migrations/versions/0008_repo_integration.py`（依赖 1）
4. `db/repositories/repos.py`（依赖 3）
5. `repos/providers/base.py`（依赖 1/2）；`github.py`、`yunxiao.py`（依赖 base）
6. `services/repos/*`（依赖 2 + 4 + 5）
7. `api/schemas/repo.py`、`api/v1/repo_*.py`、`router.py` 接线（依赖 6）
8. `config.py` / `startup.py` / `main.py` 接线；迁移与启动自检
9. 前端 `api/` → `hooks/` → `components/` → `pages/` → `routes.tsx` / `AppShell` / `ProjectsPage`
10. 测试按 TC 分批补齐（见 `docs/test-strategy.md`）
