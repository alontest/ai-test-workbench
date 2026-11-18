---
name: kb-sync
description: AlonWorkflow 知识库同步：阶段开始前把 docs/<module>/ 与 docs/_shared/ 的已有文档带入 spec 暂存区，阶段经用户确认后按合并方式提升回 docs/，关闭后追加原始需求、更新索引与域地图进度。由编排者（aw-start / aw-next / aw-close）使用；不参与 aw check / close 的判定。
---

# kb-sync — 知识库带入与提升

知识库（`docs/`）只在这里写。阶段子代理只写 `<SPEC_DIR>/` 下的暂存区；你在阶段开始前带入底稿，在用户确认后提升。
引擎不检查这里的任何事：做错了不会被拦，所以每步做完把改了哪些文件列给用户。

## 文件清单（暂存区 ↔ 知识库）

模块文件：`<SPEC_DIR>/<dir>/docs/<文件>` ↔ `docs/<module>/<docs_dir>/<文件>`；共享文件：`<SPEC_DIR>/_shared/<文件>` ↔ `docs/_shared/<文件>`。

| 阶段 | dir / docs_dir | 文件 | 合并方式 |
|---|---|---|---|
| intake | requirements-analysis / — | `_shared/domain-map.md` | 覆盖 |
| requirements-analysis | requirements-analysis | `context.md` 覆盖；`flowchart.md` 按章节（US）；`index.md` 生成 | |
| requirements-analysis | | `_shared/ontology/glossary.md`（`### TERM-Cn`）、`entities.md`（`### ENT-Cn` / `ST-Cn`）、`business-rules.md`（`### BR-Cn`）、`processes.md`（`### BP-Cn` / `API-Cn`） | 只追加 |
| interaction-design | interaction-design | `context.md`、`demo.html` 覆盖；`design-system.md` 只追加（表格行 `--token`）；`flowchart.md` 按章节（页面）；`index.md` 生成 | |
| tech-arch | technical-design | `architecture-decisions.md`（`### ADR-n`） | 只追加 |
| tech-design | technical-design | `api-spec.md`（端点）、`database-schema.md`（表）、`component-tree.md`（组件）按章节；`_shared/ontology/domain-events.md`（`### DE-Cn`）只追加 | |
| tech-tasks | technical-design | `file-structure.md`（目录）、`flowchart.md` 按章节；`context.md`、`dev-setup.md` 覆盖；`index.md` 生成 | |
| test-verification | test-verification | `regression.md`（TC）按章节；`index.md` 生成 | |

合并方式：
- **覆盖**：暂存区版本直接替换知识库版本。
- **按章节**：以 `##` 小节为单位；提升后列出新增 / 改动 / 删除的小节，删除了已有小节要请用户确认是有意的。
- **只追加**：旧条目必须原样保留，新条目用新编号；推翻旧条目时写新条目并注明 `取代：<旧编号>`。本体流程层文件（`_shared/ontology/`）的新条目必须写「对应图谱」（参考层编号或「未覆盖」）。
- **生成**：`index.md` 列出该目录下的文档与一句话说明，每次提升后重写。

## 开始阶段（aw-start / aw-next 委派前）
1. 对本阶段的每个文件：暂存区没有、知识库有 → 复制过去作为底稿。暂存区已有 → 不覆盖。
2. 在 `<SPEC_DIR>/kb-base.json` 记下每个带入文件的 sha256（`{"<知识库路径>": "<sha256 或 null>"}`），提升时用来发现别的 spec 是否在这期间改过知识库。
3. intake 开始前另写 `<SPEC_DIR>/requirements-analysis/kb-inventory.md`：`docs/<module>/`、`docs/_shared/` 与 `ontology-work/views/` 的文件清单（路径与字节数）。

## 阶段确认后（aw-next 记下确认之后）
1. 对本阶段的每个暂存文件：知识库当前的 sha256 与 kb-base.json 记的不同 → 别的 spec 改过，**不要覆盖**：把差异给用户看，合并后再提升。
2. 按合并方式检查（只追加：旧条目是否原样、编号是否重复）；有问题就列给用户，不提升。
3. 通过后复制到知识库，重写该目录的 `index.md`，更新 kb-base.json。
4. 回复里列出写入的文件；按章节合并的列出小节变化。

## 关闭后（aw-close）
1. 把 `<SPEC_DIR>/requirements-analysis/raw-requirements.md` 追加到 `docs/<module>/raw-requirements.md`，前面加一行 `## <时间> — <spec 目录名>`。
2. `docs/_shared/domain-map.md` 的 `## 域清单` 里有本模块时，在 `## 执行进度` 小节（没有就新建）里写或更新一行 `| <module> | ✅ 已完成 | <spec 目录名> | <时间> |`，表头 `| module-name | 状态 | spec | 关闭时间 |`。
3. 提醒用户把 `docs/` 与 spec 一起提交。
