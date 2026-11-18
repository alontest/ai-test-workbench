---
name: ontology
description: AlonWorkflow 本体切片：项目有本体参考层（ontology-work/views/index.json）时，按阶段从中切出与本需求相关的业务对象、实体、规则、状态、流程与候选事件，写成 <SPEC_DIR>/ontology-slices/<阶段>.md 供阶段子代理只读参考。由编排者在委派阶段子代理前使用；不参与 aw check / close 的判定。
---

# ontology — 本体切片

项目没有 `ontology-work/views/index.json`（或它的 `schema` 不认识）时什么都不做，并删掉旧的 `<SPEC_DIR>/ontology-slices/`，免得留下过期内容。
参考层由 `ontology-builder-native` / `ontology-consumption build` 从代码生成，这里只读，不改。

## index.json 的结构
`{"schema": …, "meta": {"graph_fingerprint", "counts"}, "entries": [{"id", "type", "name", "zh_name", "zh_definition" | "description", "module", "code_paths", "neighbors": [{"id"}], "processes", "zh_status"}]}`。
编号前缀即类型：BO 业务对象、ENT 实体、BR 规则、ST 状态、BP 流程、API 接口、DE 候选事件。

## 怎么切
1. **intake**：只写业务对象摘要表 `| 编号 | 中文名 | 英文名 | 所属模块 | 定义 |`（所有 `type = BusinessObject` 的条目）和各类型数量，用来判断需求落在哪个模块。
2. **其余阶段**：先找种子编号：
   - 本 spec 产物里 `涉及本体：` 行写的编号（编号后面紧跟中文时，从尾部去字直到对上 index 里的编号）；
   - 本 spec 流程层新条目（`<SPEC_DIR>/_shared/ontology/`）的「对应图谱」编号；
   - 都没有时，按名称匹配：英文名整词（不分大小写，至少 4 个字符）或中文名出现在本 spec 的产物里（不含 ontology-slices、kb-inventory.md、_shared）。
3. 种子再扩一跳 `neighbors`；切片里有某个候选事件的发布方或订阅方流程时，把这个事件也带上。
4. 按阶段只留需要的类型：requirements-analysis 留 BO / ENT / BR / ST / BP，并附业务对象摘要表；interaction-design 留 BO / ST / BP；tech-arch、tech-design、tech-tasks 全留并写出 `code_paths`；test-verification 留 BR / ST / BP / API。
5. 文件头写：图谱指纹前 12 位、怎么选的、种子编号、`zh_status` 为 pending / maybe_renamed 的编号（中文待确认）、磁盘上已不存在的 `code_paths`（标「⚠️ 磁盘上没有」）。
6. 每个条目一个 `###` 小节：`编号 中文名（英文名）`、定义、落点路径、相邻编号。末尾附本 spec 流程层条目（图谱之外的增量）。

## 用法提示（写进切片末尾）
在产物里写 `涉及本体：ENT-…、BR-…`（只写编号），下次切片按它重切；图谱里没有的新知识追加到流程层 `<SPEC_DIR>/_shared/ontology/`，写明「对应图谱」，由 skill `kb-sync` 在阶段确认后提升。
