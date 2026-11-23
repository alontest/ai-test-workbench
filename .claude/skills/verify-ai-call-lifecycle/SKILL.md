---
name: verify-ai-call-lifecycle
description: Formally check the AI call lifecycle in this repo — that no ai_call_record is left `running` once every gateway coroutine has finished (cancellation, terminal finalize, and startup merge of interrupted calls). Run it before changing `AiGateway.complete`, `_insert_running`, `_finalize`, or `merge_running_calls`; tests cover single-threaded cases only.
---

# Verify the AI call lifecycle

TLA+ model of `AiGateway.complete` (`src/workbench/services/ai_gateway.py`) plus the restart merge in
`merge_running_calls` (`src/workbench/startup.py`). TLC explores **every interleaving** of insert, finalize,
cancellation and restart for the bound in the config, instead of the handful of orders the tests run.

Property in one sentence: once every gateway coroutine has finished, no `ai_call_record` row is still
`running`.
Harm in one sentence: a row stuck at `running` is a call the user sees spinning forever; startup merge
only fixes it on the next restart, so a long-lived process shows it until then.

## Coverage record

Confirmed against commit `d3c8603` on 2026-11-19.

| Verified code | Model part |
| --- | --- |
| `src/workbench/services/ai_gateway.py:122` `record_id = await self._insert_running(...)` | `Insert` — commits a `running` row |
| `...ai_gateway.py:180,203` `await self._finalize(...)` (success/failed/timeout) | `Finalize` — terminal status + one `call` event |
| `...ai_gateway.py:163` `except asyncio.CancelledError` → `_finalize(interrupted)` | `CancelFinalized` |
| `...ai_gateway.py:128-170` the `try` that the `except` covers | boundary between `CancelFinalized` and `CancelUnhandled` |
| `...ai_gateway.py:262` `_insert_running`, `:301` `_finalize` | `Insert` / `Finalize` |
| `src/workbench/startup.py:85` `merge_running_calls` | `Restart` — every `running` row → `failed(interrupted)`, one `call` event each |
| `src/workbench/config.py` `ai_max_concurrency` | `MaxConcurrency` |

A change touches the verified code if it edits any of those functions, moves work across the
`try`/`except CancelledError` boundary, or changes when the `running` row is committed. If it does:
re-read the model against the code, rerun `run-formal.sh`, and only then move the sync commit in this
table forward. Moving the commit is an assertion that the model still describes the code — make it after
reading both, never automatically.

Not covered: retry attempt counting, `knowledge_injection` events, half-applied database commits,
multi-process concurrency, `ai_max_concurrency > 1` (the config uses 1 to keep the state space small;
raise it in the `.cfg` deliberately, the bound is a real parameter).

## Run it

```bash
.claude/skills/verify-ai-call-lifecycle/run-formal.sh
```

First run downloads `tla2tools.jar` v1.7.4 (needs `java`, present: OpenJDK 17) into `.verify/tools/`.
TLC copies the spec into `.verify/formal/` and runs there, so the checked-in `formal/` dir stays clean.
Exit `0` means no invariant was violated; non-zero with `Error: Invariant ... is violated` prints the
shortest counterexample trace.

Read the result with the pstack `statechart` skill (`/pstack:statechart`): it renders each invariant
violation as its shortest path in plain words.

## Reading a result

- `SettledWhenAllDone` violated → a coroutine ended while its row is `running`. Read the trace: if the
  step before it is `CancelUnhandled`, the cancellation landed outside the `try` that `except
  CancelledError` covers. That is a real defect, not a modeling artifact — the code has two such windows
  (see the finding below).
- `CallEventAtMostOnce` or `EventMatchesRecord` violated → a terminal row got zero or two `call` events;
  check the transaction boundary in `_finalize` / `merge_running_calls`.
- `ConcurrencyBound` violated → `active` exceeded `AW_AI_MAX_CONCURRENCY`; the semaphore in
  `AiGateway._get_semaphore` is the thing to look at.
- `TypeOK` violated → the model, not the code, is wrong (a new status value in `ai_call_record` would
  show up here first).
- A behavior TLC calls a deadlock is expected and disabled with `-deadlock`: the terminal state has no
  successors.

## Known finding at `d3c8603`

`run-formal.sh` **fails** today on `SettledWhenAllDone`. Shortest counterexample:

1. `Insert(c1)` — `_insert_running` commits `status='running'`.
2. `CancelUnhandled(c1)` — the task is cancelled before the `try:` at `ai_gateway.py:128` arms
   `except asyncio.CancelledError`, so nothing finalizes the row; the coroutine is gone.
3. `CancelBeforeInsert(c2)` — the other task ends too. `done` is all TRUE, `record[c1]` is still
   `running`, `callEvents[c1]` is 0.

Two real windows in the code, both outside the protected `try`:

- between `await self._insert_running(...)` (`:122`) returning and entering the `try` at `:128` — the
  awaits in between are the session close inside `_insert_running` and the semaphore `__aexit__`;
- the success branch's `await self._finalize(...)` at `:203`, which is written outside that `try`.

`specs/ai-test-workbench_20261117184149/technical-design/tasks.md:230` specifies the intent as
「取消时 `finally` 终结为 `failed(interrupted)`」; the code uses an `except` inside a narrower `try`.
Tests reach cancellation only after the `try` is entered, so they do not catch this.

Evidence for the failure and for the model's sensitivity (`.verify/evidence/formal/`, produced 2026-11-19):

- `current-model.txt` — current model fails on `SettledWhenAllDone`.
- `safety-only.txt` — `TypeOK`, `ConcurrencyBound`, `CallEventAtMostOnce`, `EventMatchesRecord` all pass
  on the same model with `SettledWhenAllDone` removed.
- `fixed-model.txt` — a scratch model where `CancelUnhandled` finalizes to `interrupted` passes every
  invariant, so the check is sensitive to exactly that gap.

Do not "fix" this by weakening the invariant. Either fix `complete()` (wrap the whole
insert → finalize region so cancellation always finalizes) or record the finding as accepted risk.

## Files

- `formal/AiCallLifecycle.tla` — the model; every action carries a comment pointing at the code it mirrors.
- `formal/AiCallLifecycle.cfg` — `Calls = {c1, c2}`, `MaxConcurrency = 1`, five invariants.
- `run-formal.sh` — downloader + TLC runner (the only command you need).
