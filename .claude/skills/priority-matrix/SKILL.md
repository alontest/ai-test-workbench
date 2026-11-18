---
name: priority-matrix
description: Classify a list of requirements using the MoSCoW method (Must/Should/Could/Won't). Use when PM needs to determine delivery scope and make trade-off decisions, especially when resources or time are constrained.
---

# Priority Matrix (MoSCoW)

Classify each requirement in a list into Must Have, Should Have, Could Have, or Won't Have — with a rationale for every decision.

## When to Use

- Requirements list is ready and PM needs to define delivery scope
- Resources or timeline are constrained and trade-offs must be made
- Aligning stakeholders on what's in vs. out of scope

## 输入

输入可以是调用方或用户给出的文件，也可以是对话里的内容。独立使用且没有指定时，按「内容」列括号里的默认文件名在当前目录查找。

| 项 | 必需 | 内容 | 缺失时 |
|----|------|------|--------|
| 需求清单 | 是 | 待排序的需求或功能列表 | 停止，请用户提供 |
| 约束 | 否 | 阶段、期限、团队 | 按 MVP 假设排序，并标注假设 |

示例输入（仅示意，字段不是必填项）：

```
requirementList:
  - User registration and login
  - WeChat one-click login
  - Product search
  - Product detail page
  - Shopping cart
  - Order management
  - Coupon system
  - Recommendation algorithm
  - Multi-language support
  - Dark mode

context: "MVP phase, 3-month deadline, team of 5"
```

## 输出

- 默认文件：`priority-matrix.md`
- 写入位置：调用方指定了位置就写到那里；否则写到用户指定的路径；都没有时写当前目录的 `./priority-matrix.md`。
- 格式：Markdown MoSCoW 矩阵，结构见下方「Output Format」。
- 必需小节：`## MoSCoW Priority Matrix`、`### Must Have (P0)`

## Output Format

```markdown
## MoSCoW Priority Matrix

### Must Have (P0) — Product cannot function without these
| Requirement | Rationale |
|-------------|-----------|
| User registration and login | Prerequisite for all features |
| Product search | Core user journey — can't transact without finding items |

### Should Have (P1) — Important but a workaround exists
| Requirement | Rationale |
|-------------|-----------|
| Shopping cart | Improves purchase flow; single-item direct buy is a temporary substitute |
| WeChat one-click login | Reduces friction; standard login is a viable fallback |

### Could Have (P2) — Nice to have, low impact if absent
| Requirement | Rationale |
|-------------|-----------|
| Coupon system | Marketing tool; manual discounts can substitute in MVP |
| Recommendation algorithm | Needs data volume not yet available in MVP |

### Won't Have (this release) — Explicitly deferred
| Requirement | Rationale |
|-------------|-----------|
| Multi-language support | Target market is domestic; internationalization not in scope |
| Dark mode | Visual preference only; no business value impact |
```

## Classification Criteria

| Category | Rule |
|----------|------|
| **Must Have** | Without it, the product cannot launch or operate. No workaround exists. |
| **Should Have** | Important and user-expected, but a temporary substitute exists. Omitting hurts UX but won't cause failure. |
| **Could Have** | Enhances experience. Low cost to omit. Include only if time permits. |
| **Won't Have** | Explicitly out of scope for this release. Not "never" — add to roadmap. |

## Common Mistakes to Avoid

- Must Have ≠ "everything we want" — it's the minimum viable set
- If >60% of items are Must Have, the criteria are too loose — re-evaluate
- Won't Have is not a rejection; document it in the roadmap

## Execution Rules

1. Classify every item in `requirementList` — no omissions
2. Every item must have a rationale — no classification without reasoning
3. Clarify any vague requirement before classifying it
4. Apply `context` (phase, team size, deadline) to calibrate Must vs. Should
5. Output all four categories even if one is empty
