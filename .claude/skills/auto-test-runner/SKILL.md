---
name: auto-test-runner
description: Execute test cases against a codebase and collect structured results. Use when test cases are ready and need to be run, when verifying a fix resolves a failing test, or when generating a test execution report.
---

# Auto Test Runner Skill

Execute test cases systematically and collect structured results for the QA coverage report.

## When to Use

- Test cases have been generated and are ready to execute
- Verifying that a bug fix resolves a previously failing test
- Generating the final test execution report for QA Spec

## 输入

输入可以是调用方或用户给出的文件，也可以是对话里的内容。独立使用且没有指定时，按「内容」列括号里的默认文件名在当前目录查找。

| 项 | 必需 | 内容 | 缺失时 |
|----|------|------|--------|
| 测试用例文档 | 是 | 带 TC 编号的用例列表（`./test-cases.md`） | 停止，请用户提供或先生成测试用例 |
| 项目测试配置 | 否 | 测试框架配置与测试命令 | 按「1. Identify Test Runner」探测；探测不到时所有用例标 `pending` |

## 输出

- 默认文件：`test-results.md`
- 写入位置：调用方指定了位置就写到那里；否则写到用户指定的路径；都没有时写当前目录的 `./test-results.md`。
- 格式：Markdown 执行结果表 + 失败分析，结构见「4. Output: Execution Results」。
- 必需小节：`## Execution Results`、`## Failure Analysis`
- 输出位置就是测试用例文档本身时（调用方常这样指定），原地更新它已有的执行结果小节，保留原有列（每个用例一行；不在用例下另写状态字段，结果只有这一处）；只有没有这类小节时才追加下方的表。

## Execution Workflow

### 1. Identify Test Runner

Detect the project's test framework from config files:

| File | Framework |
|------|-----------|
| `package.json` with `jest` / `vitest` / `mocha` | JavaScript/TypeScript |
| `pytest.ini` / `pyproject.toml` with `pytest` | Python |
| `pom.xml` / `build.gradle` | Java (JUnit) |
| `go.mod` | Go (testing) |
| `*.csproj` / `*.sln` | .NET (xUnit / NUnit / MSTest) |

### 2. Run Tests

Execute with a single-run flag (no watch mode):

```bash
# Jest（Jest 默认就是单次运行；没有 --run 参数，--ci 关闭交互与快照写入）
npx jest --ci --json --outputFile=test-results.json

# Vitest
npx vitest run --reporter=json --outputFile=test-results.json

# pytest（--junitxml 为内置参数，无需插件）
pytest --tb=short -q --junitxml=test-results.xml
# 仅当项目已安装 pytest-json-report 插件时可用：
# pytest --tb=short -q --json-report --json-report-file=test-results.json

# Go
go test ./... -json 2>&1 | tee test-results.json

# .NET
dotnet test --logger "trx;LogFileName=test-results.trx"
```

若存在 `.aw/config.json` 且其中配置了 `verify_cmd` 或 `tdd.stacks[].run`（TDD 栈的测试命令），优先使用这些命令；否则（没有 `.aw/` 目录或未配置）跳过这一条，直接用上面的通用命令。

### 3. Map Results to Test Cases

For each test case in the test-case document (see 输入), find the corresponding test result and update:

| TC Status | Condition |
|-----------|-----------|
| `pass` | Test ran and assertions passed |
| `fail` | Test ran but one or more assertions failed |
| `skip` | Test was skipped or excluded |
| `pending` | No corresponding automated test found |

### 4. Output: Execution Results

If the output document already has an execution-results section (for example the test-case document's own results table), update that table in place and keep its columns. Otherwise add this section:

```markdown
## Execution Results

| 用例编号 | 用例标题 | 执行状态 | 执行时间 | 备注 |
|---------|---------|---------|---------|------|
| TC-001 | {标题} | pass | {时间} | - |
| TC-002 | {标题} | fail | {时间} | {失败原因摘要} |
| TC-003 | {标题} | skip | - | 需要手动执行 |
```

## Failure Analysis

When a test fails, capture:

1. **Failure message**: The exact assertion error or exception
2. **Stack trace**: First 5 lines are usually sufficient
3. **Root cause category**:
   - `implementation_bug` — code does not match spec
   - `test_setup` — preconditions not met
   - `environment` — missing dependency or config
   - `flaky` — intermittent failure, not deterministic

## Manual Test Cases

For test cases that cannot be automated (UI interactions, exploratory tests):

- Mark status as `pending` until manually executed
- Add note: `"手动执行所需"`
- After manual execution, update status to `pass` / `fail` with timestamp

## Execution Rules

1. Never run tests in watch mode — use single-run flags only
2. Always map results back to TC-xxx IDs in the test-case document
3. A `fail` result must include a `failureReason` — never leave it blank
4. If the test suite cannot be found or run, report the blocker and list all TCs as `pending`
5. Do not modify test files to make tests pass — report failures as-is
