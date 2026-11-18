# Entities

### ENT-C10 知识库
- **对应图谱**：未覆盖
- **定义**：项目级、只读导入的业务知识集合，由 `index.json` 与可选 `.md` 文件构成；一行代表一个版本快照。
- **关键属性**：kbId、projectId、name（同项目内唯一）、version、indexGeneratedAt、entryCount、status（已就绪 / 导入失败 / 已被取代）、totalByteSize、createdAt、updatedAt、supersededByKbId
- **所属模块**：knowledge-base
- **来源 spec**：knowledge-base_20261117205011

### ENT-C11 知识库条目
- **对应图谱**：未覆盖
- **定义**：知识库中按编号索引的一条业务知识，是浏览、检索与注入的最小引用单位。
- **关键属性**：entryId、kbId、code（编号）、type（术语 / 实体 / 状态 / 业务规则 / 流程 / 接口 / 领域事件 / 其他）、title、summary、body、fields、tables、codePaths、neighbors、freshnessAt、contentDigest
- **所属模块**：knowledge-base
- **来源 spec**：knowledge-base_20261117205011
