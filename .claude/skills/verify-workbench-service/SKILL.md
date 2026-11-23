---
name: verify-workbench-service
description: Verify the AI 测试工作台 service the way an operator or API client does — launch an isolated instance, run the startup self-check, drive the HTTP surface, and prove restart recovery of interrupted AI calls. Use when a change touches workbench startup, migrations, request handling, or `AiGateway.complete`/session-event persistence, and you need evidence from a real running process rather than tests.
---

# Verify the workbench service

Drives `ai-test-workbench` (`src/workbench`, FastAPI + SQLAlchemy + Alembic) as a real process:
`alembic upgrade head` → `python -m workbench.startup` → `uvicorn` → HTTP requests and SQLite reads.
Everything here is grounded in this repo; there is no browser UI in the repo yet
(`src/workbench/main.py` only mounts `web/dist` if it exists, and it does not).

## Launch

One-time dependency install (creates `.venv`): `uv sync` at the repo root.

Then, with `<run-id>` any label you choose (for example `proof-$(date +%s)`):

```bash
.claude/skills/verify-workbench-service/verifyctl.sh start <run-id>
```

What it does, in order, from an empty data dir:

1. Picks a free loopback port, writes `<repo>/.verify/run/<run-id>/env.sh` with throwaway
   `AW_ADMIN_PASSWORD`, a fresh base64 `AW_DGSGDVJWVN_LYG` key, and
   `AW_DATABASE_URL=sqlite+aiosqlite:///<run-dir>/data/workbench.db`.
2. `alembic upgrade head` (log: `<run-dir>/alembic.log`).
3. `python -m workbench.startup` — the operator self-check (ADR-020). Non-zero exit fails the launch
   (log: `<run-dir>/startup.log`).
4. `uvicorn --factory workbench.main:create_app` in the background; its PID is in `<run-dir>/uvicorn.pid`
   (log: `<run-dir>/uvicorn.log`).

Ready means usable: the launcher polls `GET /api/v1/__verify_ready` (an unregistered path) until it gets
any HTTP status, then prints `running: pid <pid> url http://127.0.0.1:<port> http 404`.

Re-running `start <run-id>` on the same id is a **restart**: same data dir and port, so startup
recovery runs against the data the previous instance left behind. Run `stop <run-id>` first if the old
process is still alive.

Teardown: `verifyctl.sh stop <run-id>`.

## Doctor

```bash
.claude/skills/verify-workbench-service/verifyctl.sh doctor <run-id>
```

One read-only check that the instance is worth driving. It prints URL, data dir, PID, port owner,
`alembic_version`, the readiness HTTP code, and the `X-Request-Id` header, and exits non-zero unless:

- the recorded PID is alive,
- `lsof -nP -iTCP:<port> -sTCP:LISTEN` shows **our** PID owning the port,
- `alembic_version.version_num` is `0006` (`HEAD_REVISION` in `src/workbench/startup.py`),
- the readiness path returns `404`,
- the response carries a non-empty `X-Request-Id`.

## Drive

- **HTTP.** `verifyctl.sh req <run-id> <path> [extra curl args]` prints status line, headers and body.
  Example: `req <run-id> /api/v1/__verify_ready`.
- **SQL.** `verifyctl.sh sql <run-id> "<SQL>"` reads the instance's SQLite file with `sqlite3 -header -column`.
  Example: `sql <run-id> "SELECT call_id,status,error_code FROM ai_call_record"`.
- **Seed an interrupted call.** `verifyctl.sh seed-running <run-id>` inserts a project, provider, model,
  session and one `ai_call_record` with `status='running'` (created 5s ago) into the live DB, and prints
  `session_id=<n> call_id=<n>`. Use it only to reproduce what a killed process leaves behind; it is
  verification scaffolding, not a product path.
- **Restart.** `stop <run-id>` then `start <run-id>`: this is the real user path for startup recovery.

There are no product HTTP endpoints yet (batch A only mounts `/api/v1` with no routes), so HTTP proofs
cover the cross-cutting contract (request id, 404 shape), and behavior proofs go through the operator
entry point plus SQL.

## Evidence

Write proof artifacts to `<repo>/.verify/evidence/<run-id>/`. They survive `stop`.

Proof standards:

- Exercise the real entry point: `python -m workbench.startup` and real HTTP requests. Do not call
  `run_startup()` or repository functions from a script and call that a proof.
- Capture the action and the resulting state: the command plus its exit code, then the SQL read that
  shows the row changed.
- Verify side effects alongside the visible result: for the interrupted-call feature, the record row
  **and** the appended `session_event` row, and that the session status is still `in_progress`.
- A `200`/`404` alone is not proof; record the header or row you asserted on.

Suggested capture for a proof:

```bash
RUN=<run-id>; E=.verify/evidence/$RUN; V=.claude/skills/verify-workbench-service/verifyctl.sh
{ $V doctor $RUN; } 2>&1 | tee "$E/doctor.txt"
$V req $RUN /api/v1/__verify_ready | tr -d '\r' | tee "$E/request.txt"
$V sql $RUN "SELECT call_id,status,error_code,finished_at FROM ai_call_record" | tee "$E/calls-after-restart.txt"
cp .verify/run/$RUN/startup.log "$E/startup.log"
```
`mkdir -p "$E"` first.

## Cleanup

```bash
.claude/skills/verify-workbench-service/verifyctl.sh stop <run-id>
```

Kills only the PID recorded in `.verify/run/<run-id>/uvicorn.pid` (never by process name), waits up to
10s, then `kill -9` as a last resort. It removes the PID file and leaves `.verify/run/<run-id>/` and
`.verify/evidence/<run-id>/` in place. To reclaim disk after you have filed the evidence, delete the run
dir explicitly: `rm -rf .verify/run/<run-id>`.

## Helpers

`verifyctl.sh` (executable, next to this file) is the only helper. Its subcommands are `start`, `doctor`,
`req`, `sql`, `seed-running`, `stop`, as invoked above. It resolves the repo root with
`git rev-parse --show-toplevel`, so it works from a worktree.

## Feature map

Read `features/README.md` before driving; it indexes the mapped user-facing features and the baseline
conditions every recipe assumes.
