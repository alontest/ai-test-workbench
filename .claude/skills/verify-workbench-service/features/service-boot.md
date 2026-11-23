# Service boot

Starting the workbench as an operator runs a self-check that either refuses to start with a non-zero
exit and a variable-named reason, or seeds the single admin credential and brings up the service.

## Sub-features

- `boot-config` refuses to start when `AW_ADMIN_PASSWORD` is missing/blank or `AW_DGSGDVJWVN_LYG` is not
  a 32-byte base64 key; the message names the variable, never its value.
- `boot-migration` refuses to start when the database is not at Alembic head `0006`.
- `boot-seed` creates the admin credential (Argon2id) on first boot and rotates it when the configured
  password changes.
- `boot-up` starts serving on the loopback port after the self-check passes.

## How to get to it (user POV)

- Run `alembic upgrade head`, then `python -m workbench.startup`, then the ASGI server.
- Operators see the exit code (`0` pass, `1` self-check failure, `2` invalid configuration) and the log
  line `启动自检失败：...` / `启动配置非法：...`.

## Driving it with verifyctl

Preconditions:

- `.venv` exists (`uv sync`).
- You hold a `<run-id>` that either does not exist yet or whose process is stopped.

- **Happy path.** Run `verifyctl.sh start <run-id>`. Expect exit `0` and the line
  `running: pid <pid> url http://127.0.0.1:<port> http 404`. `verifyctl.sh doctor <run-id>` then prints `OK`.
- **Credential seeded.** Read the row:
  `verifyctl.sh sql <run-id> "SELECT credential_id, algorithm, length(password_hash) AS hash_len FROM admin_credential"`.
  Expect one row: `credential_id=1`, `algorithm=argon2id`, `hash_len` > 20.
- **Missing password refused.** With the instance stopped, run:
  `env -u AW_ADMIN_PASSWORD AW_DATA_DIR=.verify/run/<run-id>/data AW_DATABASE_URL=sqlite+aiosqlite:///$PWD/.verify/run/<run-id>/data/workbench.db .venv/bin/python -m workbench.startup; echo "exit=$?"`.
  Expect `exit=2` and a message naming `AW_ADMIN_PASSWORD`; the value must not appear anywhere.
- **Wrong migration head refused.** With the instance stopped:
  `verifyctl.sh sql <run-id> "UPDATE alembic_version SET version_num='0005'"`, then run the self-check
  directly with the run's env — **not** through `start`, which re-runs `alembic upgrade head` first:
  `( set -a; . .verify/run/<run-id>/env.sh; set +a; .venv/bin/python -m workbench.startup ); echo "exit=$?"`.
  Expect `exit=1` and `数据库版本 0005 不是 0006`. Restore with
  `verifyctl.sh sql <run-id> "UPDATE alembic_version SET version_num='0006'"` before the next recipe.
- **Proof.** Save the `start` stdout, `doctor` output and the `admin_credential` SQL to
  `.verify/evidence/<run-id>/service-boot.txt`.

## Gotchas

- `start` runs the self-check once and then launches uvicorn separately; a passing self-check does not
  by itself prove the HTTP server came up. Always pair it with `doctor`.
- The encryption variable is spelled `AW_DGSGDVJWVN_LYG` (built in `src/workbench/config.py`); typing
  `AW_ENCRYPTION_KEY` leaves the real variable unset and startup exits `2`.
- Startup never runs migrations. On a fresh data dir the self-check fails with `数据库未迁移到 head`
  until `alembic upgrade head` has run.
- `verifyctl.sh start` *does* run `alembic upgrade head` before the self-check, so it can never
  demonstrate the wrong-head refusal; run `python -m workbench.startup` directly for that recipe.
- Changing `AW_ADMIN_PASSWORD` between starts rotates the stored hash; that is expected, not drift.
