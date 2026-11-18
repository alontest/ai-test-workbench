---
name: tech-stack-advisor
description: Recommend a technology stack based on project requirements, team constraints, and non-functional requirements. Use when Dev needs to make and justify technology choices for frontend, backend, database, and infrastructure with documented rationale and trade-offs.
---

# Tech Stack Advisor

Recommend a technology stack for a project based on its requirements, team context, and constraints — with explicit rationale and documented alternatives for each choice.

## When to Use

- Dev is starting architecture design and needs to select technologies
- Stakeholders need a justified tech stack decision before implementation
- Evaluating trade-offs between multiple viable options

## 输入

输入可以是调用方或用户给出的文件，也可以是对话里的内容。独立使用且没有指定时，按「内容」列括号里的默认文件名在当前目录查找。

| 项 | 必需 | 内容 | 缺失时 |
|----|------|------|--------|
| 项目类型与需求 | 是 | 项目类型、关键功能、非功能需求 | 停止，请用户提供 |
| 团队与约束 | 否 | 团队规模与技能、期限、运维能力 | 按通用假设给出选项，并标注假设 |
| 现有技术栈 | 否 | 项目已有清单文件与代码 | 视为新项目，给出多种候选 |

示例输入（仅示意，字段不是必填项）：

```
projectType: "Web SaaS application with mobile support"
teamSize: 5
teamExpertise: "React, Node.js, some Python"
scalingRequirements: "1,000 concurrent users at launch, 10x growth in 12 months"
keyConstraints: "3-month deadline, limited DevOps capacity"
nonFunctionalRequirements:
  - "< 200ms API response time"
  - "99.9% uptime"
  - "GDPR compliance"
```

## 输出

- 默认文件：`tech-stack.md`
- 写入位置：调用方指定了位置就写到那里；否则写到用户指定的路径；都没有时写当前目录的 `./tech-stack.md`。
- 格式：Markdown，结构见下方「Output Format」。
- 必需小节：`## Tech Stack Recommendation`、`### Summary`、`### Detailed Decisions`

## Output Format

```markdown
## Tech Stack Recommendation: {Project Name}

### Summary
| Layer | Selected | Rationale Summary |
|-------|----------|-------------------|
| Frontend | React + TypeScript | Team expertise, ecosystem maturity |
| Backend | Node.js (Express/Fastify) | Shared language with frontend, team familiarity |
| Database | PostgreSQL | Relational data model, GDPR compliance features |
| Cache | Redis | Session management, API response caching |
| Infrastructure | Docker + Railway/Render | Low DevOps overhead, fast deployment |
| Auth | Auth.js / Clerk | Reduces implementation time, security best practices |

### Detailed Decisions

#### Frontend: React + TypeScript
- **Rationale**: Team has existing React expertise; TypeScript reduces runtime errors in a 3-month timeline
- **Alternative considered**: Vue 3 — comparable DX but lower team familiarity increases ramp-up risk
- **Trade-off**: Larger bundle size vs. Next.js SSR, acceptable for SaaS dashboard use case

#### Backend: Node.js + Fastify
- **Rationale**: Shared language reduces context switching; Fastify outperforms Express by ~2x for JSON throughput
- **Alternative considered**: Python/FastAPI（更适合 ML）或 ASP.NET Core（若团队以 .NET 为主）— 按团队技能与约束选择，不是固定预设
- **Trade-off**: Single-threaded model requires careful async handling for CPU-intensive tasks

#### Database: PostgreSQL
- **Rationale**: ACID compliance for transactional data; row-level security supports GDPR data isolation
- **Alternative considered**: MongoDB — flexible schema but weaker consistency guarantees for financial data
- **Trade-off**: Schema migrations require more planning than document stores

### Scaling Plan
| Phase | Users | Architecture Change |
|-------|-------|---------------------|
| Launch | ~1,000 | Single server, vertical scaling |
| 6 months | ~5,000 | Read replicas, Redis caching layer |
| 12 months | ~10,000 | Horizontal scaling, CDN, queue-based async jobs |
```

## Decision Criteria

| Factor | Weight | Notes |
|--------|--------|-------|
| Team expertise | High | Unfamiliar tech adds 20–40% time overhead |
| Timeline fit | High | Avoid technologies requiring >1 week ramp-up |
| Scaling headroom | Medium | Must support 10x without full rewrite |
| Community/ecosystem | Medium | Active ecosystem = faster problem resolution |
| Operational complexity | Medium | Match DevOps capacity of the team |
| License/cost | Low | Flag any non-OSS or usage-based cost surprises |

## Execution Rules

1. Every technology choice must include: rationale, one alternative considered, and the trade-off accepted
2. Flag any choice that conflicts with stated constraints (deadline, team size, expertise)
3. Include a scaling plan showing when architecture changes are needed
4. Do not recommend technologies the team has zero experience with unless the alternative is clearly worse
5. If requirements are contradictory (e.g. "no DevOps capacity" + "Kubernetes"), flag the conflict explicitly
6. Do **not** preset a language or framework. When the repo has no existing stack, propose at least two backend options and two frontend options (for example .NET / Node.js / Python / Go, and React / Vue / other). If `.aw/packs/<name>/pack.json` exists for a candidate stack, mention those pack conventions when the stack matches, but do not treat any pack as a global default. If there is no `.aw/` directory, skip this check.
