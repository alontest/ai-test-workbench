---
name: task-breakdown
description: Decompose user stories and technical requirements into structured, independently deliverable development tasks. Use when Dev needs to convert a confirmed Dev Spec into an actionable task list with priority, complexity, and dependency mapping.
---

# Task Breakdown

Decompose user stories and architecture decisions into structured development tasks — each independently deliverable, sized at M or smaller, with explicit priority and dependencies.

## When to Use

- Dev Spec architecture and tech stack are confirmed
- User stories from BA Spec are confirmed and ambiguity-free
- Need to produce an actionable task list for sprint planning or implementation

## 输入

输入可以是调用方或用户给出的文件，也可以是对话里的内容。独立使用且没有指定时，按「内容」列括号里的默认文件名在当前目录查找。

| 项 | 必需 | 内容 | 缺失时 |
|----|------|------|--------|
| 用户故事 | 是 | 用户故事与 AC（`./user-stories.md`） | 停止，请用户提供 |
| 架构与技术栈 | 否 | 已确认的架构与技术栈（`./architecture-decisions.md`） | 按项目现有代码推断，并在任务描述中注明假设 |
| 文件结构与环境 | 否 | 文件清单与环境配置（`./file-structure.md`、`./dev-setup.md`） | 任务里写到目录级，不编造具体文件名 |

示例输入 (an illustrative password-reset feature; replace it with your own user stories and stack — none of these values is required):

```
userStories:
  - "US-001: User can reset password via email (P0)"
  - "US-002: User can update profile information (P1)"
architecture: "React + Node.js/Fastify + PostgreSQL + Redis"
techStack: "TypeScript, Prisma ORM, JWT auth, SendGrid for email"
```

## 输出

- 默认文件：`task-list.md`
- 写入位置：调用方指定了位置就写到那里；否则写到用户指定的路径；都没有时写当前目录的 `./task-list.md`。
- 格式：Markdown 任务列表，结构见下方「Output Format」；调用方要求复选框格式时按其中的复选框规则写。
- 必需小节：`## Task List:`

## Output Format

The heading-style example below is the default format. When the caller asks for a checkbox task list (a file that other tools parse), use the checkbox format in the next paragraph instead.

> **调用方要求复选框任务列表时**：每个任务必须是一行复选框
> `- [ ] TASK-TD-NNN：<动作>`，下面的字段缩进为子项。读取这份文件的工具只解析这种复选框行（任务进度、TDD、
> 实现步骤都依赖它），下例中的 `### TASK-001:` 标题格式不会被识别。格式示例（任务内容取自下方的密码重置示例，仅示意格式，实际按你的任务填写；`...` 表示省略）：
>
> ```markdown
> - [ ] TASK-TD-001：Set up password reset token schema
>   - **Description**: ...
>   - **Dependencies**: None
> ```

Example output for the example input above (illustrative only; `{Project Name}` is a placeholder for your project's name):

```markdown
## Task List: {Project Name}

### TASK-001: Set up password reset token schema
- **Description**: Add `password_reset_tokens` table via Prisma migration. Fields: id, user_id (FK), token (hashed), expires_at, used_at. Index on token for lookup performance.
- **Priority**: P0
- **Complexity**: S (< 1 day)
- **Related requirements**: US-001, AC-001-1
- **Dependencies**: none

### TASK-002: Implement POST /auth/forgot-password endpoint
- **Description**: Accept email, look up user, generate secure random token, hash and store in DB, send reset email via SendGrid. Return generic 200 regardless of whether email exists (prevent user enumeration).
- **Priority**: P0
- **Complexity**: M (2–3 days)
- **Related requirements**: US-001, AC-001-1, AC-001-4
- **Dependencies**: TASK-001

### TASK-003: Implement POST /auth/reset-password endpoint
- **Description**: Accept token + new password. Validate token exists, not expired (24h), not used. Hash new password, update user record, mark token as used. Return 200 on success, 400 on invalid/expired token.
- **Priority**: P0
- **Complexity**: M (2–3 days)
- **Related requirements**: US-001, AC-001-2, AC-001-3
- **Dependencies**: TASK-001

### TASK-004: Build reset password UI flow (request + confirmation pages)
- **Description**: Two pages: (1) email input form with loading/success/error states per wireframe WF-003; (2) new password form with confirmation field and policy validation. Use design tokens from UX Spec.
- **Priority**: P0
- **Complexity**: M (2–3 days)
- **Related requirements**: US-001, AC-001-1, AC-001-2
- **Dependencies**: TASK-002, TASK-003
```

## Complexity Scale

| Size | Time Estimate | Rule |
|------|--------------|------|
| XS | < 4 hours | Config change, copy update, trivial fix |
| S | < 1 day | Single endpoint, simple component, DB migration |
| M | 2–3 days | Feature slice with frontend + backend + tests |
| L | ~1 week | Too large — split into XS/S/M tasks before adding to the list |
| XL | > 1 week | Too large — split into XS/S/M tasks before adding to the list |

Only XS, S and M may appear in the task list. L and XL exist only to recognise tasks that must be split.

## Priority Levels

| Level | Meaning |
|-------|---------|
| P0 | Blocks launch — must be done first |
| P1 | Important — do after all P0s are complete |
| P2 | Nice to have — do if time permits |
| P3 | Deferred — schedule for next iteration |

## Decomposition Rules

1. Every task must map to at least one user story AC — no orphan tasks
2. Maximum complexity is M. If a task would be L or XL, split it into XS/S/M tasks first; never output a task marked L or XL
3. P0 tasks must be listed first and form a clear critical path
4. Every task with a dependency must explicitly list it
5. Each task description must include enough detail for a developer to start without asking questions
6. Infrastructure/setup tasks (DB schema, auth middleware, CI pipeline) are valid tasks — list them first as they unblock feature tasks
7. Do not create tasks for work already covered by a library or framework out of the box
