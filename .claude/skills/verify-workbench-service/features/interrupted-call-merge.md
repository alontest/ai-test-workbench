# Interrupted call recovery

When the service stops while an AI call is recorded as `running`, the next startup turns that record
into a terminal `failed(interrupted)` row with a matching `call` event, so a session never shows a call
that is silently stuck forever.

## Sub-features

- `merge-status` flips every `running` `ai_call_record` to `status='failed'`, `error_code='interrupted'`
  with `finished_at` and a computed `latency_ms`.
- `merge-event` appends exactly one `session_event` of type `call` with `errorCode='interrupted'`
  and `actor='system'` for the merged record.
- `merge-session-open` leaves the session `in_progress`, so the user can keep typing after recovery.
- `merge-idempotent` does not touch records that are already terminal.

## How to get to it (user POV)

- A user's call is in flight when the process dies; the record stays `running` in the database.
- The operator starts the service again (`python -m workbench.startup` + server); the user reopens the
  session and sees the call as failed/interrupted instead of a spinning "running" state.

## Driving it with verifyctl

Preconditions:

- `verifyctl.sh doctor <run-id>` prints `OK` (the instance is up and migrated).

- **Reproduce the crash residue.** `verifyctl.sh seed-running <run-id>` prints
  `session_id=<n> call_id=<n>`; note both. Confirm the residue:
  `verifyctl.sh sql <run-id> "SELECT call_id,status FROM ai_call_record WHERE call_id=<call>"` → `running`.
- **Restart for real.** `verifyctl.sh stop <run-id>` then `verifyctl.sh start <run-id>`. Expect exit `0`,
  a `running: pid ...` line, and `startup.log` containing `merged 1 running ai calls`.
- **Record settled.** `verifyctl.sh sql <run-id> "SELECT status,error_code,latency_ms,finished_at FROM ai_call_record WHERE call_id=<call>"`.
  Expect `failed`, `interrupted`, `latency_ms >= 5000`, non-null `finished_at`.
- **One event appended.** `verifyctl.sh sql <run-id> "SELECT type,json_extract(payload,'$.errorCode') AS code FROM session_event WHERE session_id=<session>"`.
  Expect exactly one `call` / `interrupted` row.
- **Session still open.** `verifyctl.sh sql <run-id> "SELECT status FROM analysis_session WHERE session_id=<session>"` → `in_progress`.
- **Terminal rows untouched.** `verifyctl.sh sql <run-id> "SELECT call_id,status FROM ai_call_record"` shows
  earlier `success`/`failed`/`timeout` rows unchanged after a second restart.
- **Proof.** Save the seed output, both SQL reads before restart, the restart stdout and both SQL reads
  after restart to `.verify/evidence/<run-id>/interrupted-call-merge.txt`.

## Gotchas

- `seed-running` writes the `running` row directly; do not treat it as a product path. It is the only way
  to reproduce a killed process without actually killing one.
- `start <run-id>` on a live instance is a no-op. You must `stop` first, or the old process keeps the
  port and the new one never starts.
- `startup.log` is overwritten on every start; copy it into the evidence dir before another restart.
- Startup does not append an event when the session row is missing (it guards `session is not None`).
  Seed through `seed-running` so the session exists.
- `latency_ms` is computed from `created_at`, and `seed-running` backdates it by 5s; a fresh row would
  report a near-zero latency and look like a failure.
