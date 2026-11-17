# AI 测试工作台

给 [AlonWorkflow](../AlonWorkflow) 0.7.0 跑全流程用的干净试验场。
产品本身也是这个仓库要长出来的东西：记录、筛选、回放一批 AI 测试用例。

功能不要手写，走 `aw-start` → 确认 → 开发 → `aw verify` → `aw review run` → `aw close`。

```bash
python3 .aw/aw.py status
python3 .aw/aw.py check
```
