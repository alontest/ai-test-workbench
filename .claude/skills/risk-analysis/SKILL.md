---
name: risk-analysis
description: Identify technical risks and generate mitigation strategies for a project based on its architecture, tech stack, and requirements. Use when Dev needs to surface implementation risks before task breakdown, especially for high-complexity or high-stakes features.
---

# Risk Analysis

Identify technical risks in a project's architecture and requirements, assess their impact and probability, and generate concrete mitigation strategies.

## When to Use

- Dev has completed architecture design and needs to surface risks before task breakdown
- A feature has high complexity, tight deadlines, or unfamiliar technology
- Stakeholders need a risk register before committing to a delivery plan

## 输入

输入可以是调用方或用户给出的文件，也可以是对话里的内容。独立使用且没有指定时，按「内容」列括号里的默认文件名在当前目录查找。

| 项 | 必需 | 内容 | 缺失时 |
|----|------|------|--------|
| 架构与关键功能 | 是 | 架构描述、关键功能（`./tech-stack.md`） | 停止，请用户提供 |
| 约束 | 否 | 期限、团队、运维能力 | 按中等约束评估，并标注假设 |

示例输入（仅示意，字段不是必填项）：

```
architecture: "React SPA + Node.js API + PostgreSQL + Redis"
keyFeatures:
  - "Real-time collaborative editing"
  - "File upload up to 100MB"
  - "Third-party payment integration"
constraints: "3-month deadline, team of 5, no dedicated DevOps"
```

## 输出

- 默认文件：`risk-register.md`
- 写入位置：调用方指定了位置就写到那里；否则写到用户指定的路径；都没有时写当前目录的 `./risk-register.md`。
- 格式：Markdown 风险登记表 + 风险详情，结构见下方「Output Format」。
- 必需小节：`## Risk Register`、`### Risk Detail`

## Output Format

```markdown
## Risk Register: {Project Name}

| ID | Risk | Category | Impact | Probability | Score | Mitigation |
|----|------|----------|--------|-------------|-------|------------|
| RISK-001 | Real-time sync conflicts under concurrent edits | Technical | High | High | 🔴 Critical | Use CRDT or OT algorithm; prototype in week 1 |
| RISK-002 | 100MB file upload timeout on slow connections | Technical | Medium | Medium | 🟡 Medium | Chunked upload with resumable protocol (tus.io) |
| RISK-003 | Payment provider API changes breaking checkout | Integration | High | Low | 🟡 Medium | Abstract payment layer; pin SDK version; monitor changelog |
| RISK-004 | No DevOps capacity for production incidents | Operational | High | Medium | 🔴 Critical | Use managed services (Railway/Render); set up alerts day 1 |

### Risk Detail

#### RISK-001: Real-time sync conflicts
- **Description**: Multiple users editing the same document simultaneously may produce conflicting states that are difficult to merge correctly
- **Impact**: High — data loss or corruption directly affects core product value
- **Probability**: High — concurrent editing is the primary use case
- **Mitigation**:
  1. Evaluate Yjs (CRDT library) in week 1 spike — 3 days max
  2. If Yjs integration is too complex, fall back to last-write-wins with conflict notification
  3. Add integration tests simulating 5 concurrent editors before feature sign-off
- **Contingency**: If mitigation fails, descope real-time to async collaboration (Google Docs-style suggestions) for MVP
```

## Risk Categories

| Category | Examples |
|----------|---------|
| **Technical** | Algorithm complexity, performance bottlenecks, data consistency |
| **Integration** | Third-party API reliability, version compatibility, rate limits |
| **Operational** | Deployment complexity, monitoring gaps, incident response |
| **Scope** | Requirement ambiguity, feature creep, underestimated complexity |
| **Team** | Knowledge gaps, key-person dependency, onboarding time |

## Risk Scoring Matrix

| | Low Impact | Medium Impact | High Impact |
|--|-----------|--------------|-------------|
| **High Probability** | 🟡 Medium | 🔴 Critical | 🔴 Critical |
| **Medium Probability** | 🟢 Low | 🟡 Medium | 🔴 Critical |
| **Low Probability** | 🟢 Low | 🟢 Low | 🟡 Medium |

## Execution Rules

1. Identify at minimum one risk per major architectural component
2. Every risk must have: description, impact, probability, score, and at least one concrete mitigation step
3. Critical risks (🔴) must include a contingency plan if mitigation fails
4. Flag any risk that could require scope reduction — surface it early
5. Risks that are actually BA/UX ambiguities should be logged as DEVAMB items, not RISK items
