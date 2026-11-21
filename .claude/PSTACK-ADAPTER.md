# pstack 在本项目的适配说明

> 核实时间：2026-11-20 17:00（Asia/Shanghai）。来源：`pstack@cursor-plugins` 0.15.44。
> 这份文件记录**哪些能力完整可用、哪些做了裁剪**。裁剪项都是实测结论，不是推测。

## 为什么需要适配

pstack 是 Cursor 生态的插件。它在 Claude Code 下能用，但有三处结构性差异需要处理：

1. 57/58 个 skill 带 `disable-model-invocation: true`，模型看不到，只能靠人手敲斜杠命令。我们的流程是「对话里分派任务」，没有手敲的时机。
2. 大量 skill 之间有互相引用（`architect`、`swarm`、`arena`、24 个 `principle-*`）。只复制 `poteto-mode` 会导致它引用一堆不存在的 skill。
3. 模型 slug 是 Cursor 命名（`claude-opus-5-5-xhigh-fast`），Claude Code 的 Task 工具只认 `sonnet` / `opus` / `haiku` / `fable`。

## 已做的适配

| 项 | 做法 |
| --- | --- |
| 模型可见性 | 复制到 `.claude/skills/` 与 `.claude/agents/`，删除全部 `disable-model-invocation: true`（32 个文件） |
| 依赖完整性 | 复制 `poteto-mode` 全部 playbooks + `worker.md`，加 24 个 `principle-*`、9 个关联 skill、`figure-it-out`，共 39 个 skill |
| 路径断裂 | 补 `.claude/docs/harness/claude-code.md`；把 `~/.cursor/rules/pstack-models.mdc` 改指 `~/.claude/rules/pstack-models.md` |
| 模型 slug | `poteto-agent.md` 的 `model` 从 `claude-opus-5-5-xhigh-fast` 改为 `opus` |

### 校验结果

- 相对 `.md` 引用 13 条，全部可解析
- 被引用的 25 个 skill 名，全部已安装
- 13 个关键 skill 在会话内可见（实测 `claude -p` 返回全 yes）

## 裁剪项（必须知道）

### 1. 模型无法按角色分档 —— 影响最大

pstack 的设计前提是「不同角色跑不同模型」：重度判断用 Opus 5.5 xhigh，机械改动用 Opus 5.5 high，评审面板混用 Claude / Gemini。

你的环境通过 magpie（`127.0.0.1:3425`）把所有档位都路由到同一个模型：

```json
"ANTHROPIC_DEFAULT_SONNET_MODEL": "auto/deepseek-v4.1-flash[1m]",
"ANTHROPIC_DEFAULT_OPUS_MODEL":   "auto/deepseek-v4.1-flash[1m]",
"ANTHROPIC_DEFAULT_HAIKU_MODEL":  "auto/deepseek-v4.1-flash[1m]"
```

**后果**：

- `swarm` / `arena` / `interrogate` 的多模型协作退化为同一个模型跑多次。`arena` 的跨厂商评审（「judge 不能来自父代理同一厂商」）失去意义。
- `poteto-mode` 里「按难度调整 reasoning 档位」的指令实际无效。
- 每个 playbook 依赖的角色配置（`feature, refactoring` / `bug-fix` 等行）读不到差异。

**还能用的部分**：`poteto-mode` 的原则、playbook 的步骤顺序、`worker.md` 的交付规范、`unslop` 的文风、`blast-radius` 的影响面分析。这些不依赖模型差异。

**想恢复分档**：在 magpie 里给不同档位配不同上游模型，或在 Claude Code 里切到 `cursor/claude-opus-5-5@1m` 这类真实 Claude 模型。

### 2. `cursor-team-kit` 插件里的命令不可用

`poteto-mode` 提到两个外部命令：

- `/deslop`（提交前）
- `control-ui` / `control-cli`（发 UI / CLI 时）

`cursor-team-kit` 未安装，这两个不可用。**替代**：`unslop` skill 已在本地，可用于去 AI 味。

### 3. `poteto-agent` 的模型从 xhigh 降为默认 opus

原值 `claude-opus-5-5-xhigh-fast` 在本会话被 Task 工具拒绝（实测确认）。改成 `opus` 后能正常派生，但拿不到 xhigh 档位——反正上面第 1 条已经让档位失效，实际无差别。

### 4. 未复制的 skill

58 个里复制了 39 个。未复制的 19 个是使用频率低或依赖外部插件的：`ketchup`、`ketchup-video`、`make-bot-ui`、`create-formal-verification-skill`、`maintain-formal-verification-skill`、`setup-pstack` 等。需要时从 `~/.claude/plugins/cache/cursor-plugins/pstack/0.15.44/skills/` 补。

## 与 pstack 上游的偏差

升级 pstack 时，以下文件不会自动同步，需要手工对比：

```
.claude/skills/            39 个 skill 副本
.claude/agents/poteto-agent.md   改了 model 字段
.claude/docs/harness/claude-code.md
```

对比命令：

```bash
P=~/.claude/plugins/cache/cursor-plugins/pstack/<新版本>
diff -r $P/skills .claude/skills | head -50
```

## 怎么确认它真的在用

`AGENTS.md` 里的规则是上下文，不是强制。唯一可信证据是工具调用序列：

```bash
python3 scripts/check_poteto.py <pane-id>
python3 scripts/check_poteto.py --list
```

退出码 0 = 调用过 `Skill(poteto-mode)`，1 = 没调用。
