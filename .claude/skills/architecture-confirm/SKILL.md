---
name: architecture-confirm
description: 扫描项目现有架构，逐项整理前端/后端/数据库/部署决策（ADR），请用户确认后锁定。当用户要求确认、梳理或锁定技术架构，或在拆分开发任务前需要先定下技术选型时使用。
---

# Skill: architecture-confirm — 技术架构确认

## 职责

有了技术方案草稿、准备拆分开发任务时，先扫描项目现有架构，再与用户逐项确认前端、后端、数据库、部署等所有架构决策，确保技术选型无歧义，避免开发时返工。

---

## 输入

输入可以是调用方或用户给出的文件，也可以是对话里的内容。独立使用且没有指定时，按「内容」列括号里的默认文件名在当前目录查找。

| 项 | 必需 | 内容 | 缺失时 |
|----|------|------|--------|
| 项目代码 | 是 | 当前仓库的文件结构与清单文件（步骤 0 扫描） | 视为新项目，所有决策项标为待定 |
| 技术选型草稿 | 否 | 候选技术栈与架构草稿（`./tech-stack.md`） | 以扫描结果为准，待定项写入确认清单 |
| 业务约束 | 否 | 需求摘要、性能与合规约束 | 在确认清单中请用户补充关键约束 |

## 输出

- 默认文件：`architecture-decisions.md`
- 写入位置：调用方指定了位置就写到那里；否则写到用户指定的路径；都没有时写当前目录的 `./architecture-decisions.md`。
- 格式：Markdown ADR 记录，每条决策以 `ADR-NNN` 编号，结构见下方「输出格式」。
- 必需小节：`# Architecture Decisions Record (ADR)`、`## 已确认决策`、`### ADR-001`

---

## 执行步骤

### 步骤 0：项目扫描（MANDATORY，必须最先执行）

**在展示任何架构决策前，必须先扫描项目，检测已有架构**：

不要预设某种语言或框架。已有栈请用户确认是否沿用；新项目或无法判断时，结合 skill `tech-stack-advisor` 给出多种选项，写入确认清单请用户决定。用户确认后，若存在 `.aw/install.json` 且其中装有与选型匹配的 pack，则加载 `.aw/packs/<name>/pack.json` 中对应的约定；否则（没有 `.aw/` 目录或没有匹配的 pack）跳过这一步，只按用户确认的选型继续。

```
扫描目标文件/目录：
  ├── package.json / *.csproj / *.sln / pom.xml / go.mod / pyproject.toml / requirements.txt / Cargo.toml
  │     → 识别语言、运行时、已安装依赖
  ├── vite.config.ts / webpack.config.js / next.config.js
  │     → 识别前端构建工具和框架
  ├── src/ 目录结构
  │     → .tsx/.jsx 文件 → React 项目
  │     → .vue 文件 → Vue 项目
  │     → api/、services/、request/、http/ 或 *client* 等 → 识别已有 HTTP 客户端或封装（axios/fetch/ky 实例、OpenAPI 生成的 client 等）
  │     → src/app/components/ui/ → 已有组件库
  ├── server/ / api/ / backend/ / app/ 目录
  │     → 识别后端框架（ASP.NET Core / Express / NestJS / FastAPI / Spring 等）
  ├── prisma/schema.prisma / migrations/ / *.sql
  │     → 识别数据库类型和 ORM
  ├── docker-compose.yml / Dockerfile
  │     → 识别部署方式和基础设施
  └── .env / .env.example
        → 识别已配置的服务和环境变量
```

**扫描结论输出格式**：

> **项目架构扫描结论**
>
> | 层次 | 检测结果 | 置信度 |
> |------|---------|--------|
> | 前端框架 | React 18 + Vite（检测到 package.json + .tsx 文件） | 高 |
> | 前端组件库 | 已有 src/app/components/ui/（shadcn/ui 封装） | 高 |
> | 前端 API 层 | 已有统一 HTTP 客户端（检测到 src/api 下的 axios 封装） | 高 |
> | 后端框架 | NestJS（检测到 nest-cli.json） | 高 |
> | 数据库 | PostgreSQL + Prisma（检测到 prisma/schema.prisma） | 高 |
> | 缓存 | 未检测到 | — |
> | 部署 | Docker（检测到 docker-compose.yml） | 中 |
>
> 已有架构将作为默认选型，以下确认清单中标注"已有"的项目仍需用户确认是否沿用。

---

### 步骤 1：架构决策确认清单

基于扫描结果，逐项列出需要用户确认的架构决策。**已检测到的选型标注"已有"，未检测到的标注"待定"**：

**前端架构**
- 框架与版本（React / Vue / Svelte / 其他，以探测或用户选择为准，不要预设）
- 状态管理方案（Context / Zustand / Redux / Pinia）
- 路由方案（React Router / Next.js App Router / Vue Router）
- 样式方案（Tailwind / CSS Modules / Styled Components）
- 构建工具（Vite / Webpack / Turbopack）
- 组件库（已有 shadcn/ui 封装 / Element Plus / 从零搭建）
- API 调用层（已有 HTTP 客户端/封装 / 从零搭建 / 其他）

**后端架构**（如适用）
- 运行时与语言（.NET / C#、Node.js、Python、Go、Java 等，以探测或用户选择为准，不要预设）
- 框架（ASP.NET Core / Express / Fastify / NestJS / FastAPI / Spring Boot / 其他）
- ORM / 数据访问层（EF Core / Prisma / TypeORM / Drizzle / SQLAlchemy / 其他）
- 认证方案（JWT / Session / OAuth / SSO）
- API 风格（REST / GraphQL / tRPC）

**数据库**
- 主数据库类型（PostgreSQL / MySQL / SQLite / MongoDB）
- 缓存层（Redis / 内存缓存 / 无）
- 文件存储（本地 / S3 / Cloudinary）

**部署与基础设施**
- 部署目标（Vercel / Docker / 本地 / 云服务）
- 环境变量管理方式
- CI/CD 需求

---

### 步骤 2：展示确认清单

以表格形式展示所有决策，标注状态：

```markdown
| 决策项 | 当前选型 | 来源 | 状态 | 备注 |
|--------|---------|------|------|------|
| 前端框架 | React 18 + Vite | 已有 | ✅ 请确认沿用 | |
| 组件库 | shadcn/ui 封装 | 已有 | ✅ 请确认沿用 | |
| 状态管理 | Zustand | 待定 | ⚠️ 待确认 | 是否需要持久化？ |
| 后端框架 | NestJS | 已有 | ✅ 请确认沿用 | |
| 数据库 | PostgreSQL + Prisma | 已有 | ✅ 请确认沿用 | |
| 缓存层 | 未检测到 | 待定 | ⚠️ 待确认 | 是否需要 Redis？ |
```

**每个"待确认"项必须等待用户明确回复后才能继续**，不得自行假设。

---

### 步骤 3：处理疑问与分歧

对每个"待确认"或用户提出疑问的项，提供：
- 当前选型的理由
- 备选方案对比表
- 推荐选择及依据

---

### 步骤 4：锁定架构

用户逐项确认所有决策后，生成"架构锁定声明"，之后的设计与开发不得更改已锁定的技术选型。

---

## 输出格式

结构如下（写入位置见「输出」）：

```markdown
# Architecture Decisions Record (ADR)

## 锁定时间
{YYYY-MM-DD HH:mm}

## 项目扫描摘要
| 层次 | 检测结果 | 置信度 |
|------|---------|--------|

## 已确认决策

### ADR-001：前端框架
- **决策**：{选择了什么}
- **来源**：{已有 / 新增}
- **状态**：✅ 已锁定
- **理由**：{依据}
- **影响**：{对开发的影响}

### ADR-002：后端框架
- **决策**：{选择了什么}
- **来源**：{已有 / 新增}
- **状态**：✅ 已锁定
- **理由**：{依据}
- **影响**：{对开发的影响}

（以此类推，前后端每项决策各一条 ADR）

## 约束条件
- {不可更改的约束}

## 状态
architecture-locked
```

---

## 澄清检查点（ARCHAMB）

以下情况必须在确认前解决：
- 检测到的已有架构与需求存在冲突
- 技术选型与已有基础设施冲突
- 选型存在许可证风险
- 团队对某技术无经验
- 选型会导致显著的性能或安全问题
