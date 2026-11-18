---
name: component-breakdown
description: 将线框图与组件清单拆为可复用组件树，明确每个组件的职责、Props、状态与依赖。当用户要求拆分组件、设计组件树或规划前端组件结构时使用。
---

# Skill: component-breakdown — 组件拆分

## 职责

基于交互设计的线框图和组件清单，将 UI 拆分为可复用的原子组件树，明确每个组件的职责、Props、状态和依赖关系。

---

## 输入

输入可以是调用方或用户给出的文件，也可以是对话里的内容。独立使用且没有指定时，按「内容」列括号里的默认文件名在当前目录查找。

| 项 | 必需 | 内容 | 缺失时 |
|----|------|------|--------|
| 线框图与组件清单 | 否 | 页面线框图、组件清单（`./wireframes.md`） | 从现有界面代码识别组件，并在 COMPAMB 中注明没有线框图 |
| Design Tokens | 否 | 颜色、字体、间距等变量（`./design-tokens.md`） | 沿用项目现有样式变量，不新增 |
| 交互约定 | 否 | 关键交互与组件状态 | 按通用状态 default / loading / error / empty 拆分 |

## 输出

- 默认文件：`component-tree.md`
- 写入位置：调用方指定了位置就写到那里；否则写到用户指定的路径；都没有时写当前目录的 `./component-tree.md`。
- 格式：Markdown 组件树 + Props 接口，结构见下方「输出格式」。
- 必需小节：`# Component Tree`、`## 组件层级总览`、`## Props 接口定义`

---

## 执行步骤

### 步骤 1：识别组件层级

从线框图中提取所有 UI 元素，按 Atomic Design 分层：
- **Atoms**：Button、Input、Icon、Badge 等不可再拆分的基础元素
- **Molecules**：由 Atoms 组合的功能单元（如 SearchBar = Input + Button）
- **Organisms**：由 Molecules 组合的页面区块（如 Header、ProductCard）
- **Templates**：页面布局骨架
- **Pages**：完整页面，对应 US

### 步骤 2：定义组件接口

每个组件必须明确：
- Props 类型定义（TypeScript interface）
- 内部状态（useState 列表）
- 触发的事件（onXxx 回调）
- 依赖的子组件

### 步骤 3：识别可复用组件

标记跨页面复用的组件，避免重复实现。

### 步骤 4：生成组件树

用缩进树形结构表示组件嵌套关系。

---

## 输出格式

结构如下（写入位置见「输出」）：

```markdown
# Component Tree

## 组件层级总览

### Atoms
| 组件名 | 文件路径 | Props | 状态 | 复用次数 |
|--------|---------|-------|------|---------|
| Button | `src/components/atoms/Button.tsx` | variant, size, disabled, onClick | - | {N} |

### Molecules
| 组件名 | 文件路径 | 包含 Atoms | Props | 状态 |
|--------|---------|-----------|-------|------|

### Organisms
| 组件名 | 文件路径 | 包含 Molecules | 关联 US |
|--------|---------|--------------|---------|

### Pages
| 页面名 | 文件路径 | 关联 US | 路由 |
|--------|---------|---------|------|

## 组件树（嵌套结构）

### {页面名}（US-{NNN}）
```
Page
├── Header (Organism)
│   ├── Logo (Atom)
│   └── NavBar (Molecule)
│       └── NavItem (Atom) × N
└── MainContent (Organism)
    └── {ComponentName} (Molecule)
```

## Props 接口定义

### {ComponentName}
```typescript
interface {ComponentName}Props {
  // props 定义
}
```

## 可复用组件清单
| 组件名 | 复用场景 | 注意事项 |
|--------|---------|---------|
```

---

## 澄清检查点（COMPAMB）

以下情况标记为 COMPAMB，需用户确认：
- 组件职责边界不清晰
- 状态应放在父组件还是子组件
- 是否需要全局状态管理（Redux/Zustand）
- 组件是否需要懒加载
