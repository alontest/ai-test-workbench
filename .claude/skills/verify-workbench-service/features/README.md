# Workbench service verification map

This directory is the maintained source for verifying the user-facing behavior of the AI 测试工作台
service. Read this index before driving the app, then use the matching feature file as the recipe.

## Baseline preconditions

- `uv sync` has been run in the repo (`.venv` exists).
- Launch with `.claude/skills/verify-workbench-service/verifyctl.sh start <run-id>`, which creates a
  disposable data dir under `.verify/run/<run-id>/data` so concurrent runs never share state.
- Never drive an instance this verification run did not start. `doctor` must print `OK` first.
- The instance must be migrated to Alembic head `0006`; a data dir from an older head fails startup
  on purpose (see `service-boot.md`).

## Driving conventions

- Start every recipe from the baseline state unless its preconditions say otherwise.
- Treat every command as literal; replace only `<run-id>` and the SQL you are running.
- Run HTTP actions through `verifyctl.sh req`, SQL reads through `verifyctl.sh sql`.
- Restore seeded data after a mutation. Do not remove proof artifacts during cleanup.
- There is no browser surface and no product endpoint yet; do not invent one to make a recipe pass.

## Proof and skip reporting

- Capture the user action and the resulting state, not only the final output.
- Command proof includes the command, stdout/stderr, and exit code.
- Mutation proof includes a read-only second view of the stored value (`sql`).
- Record the feature ID and entry point used with every artifact.
- Report an unreachable path with the attempted command and the unmet precondition.
- Do not report a skipped entry point as verified through a different path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It
then uses exactly four H2 sections in this order: `Sub-features`, `How to get to it (user POV)`,
`Driving it with verifyctl`, `Gotchas`.

## Features

- [Service boot](./service-boot.md) covers the operator startup self-check: config validation, migration
  head, and admin credential seeding.
- [Request identity](./request-id.md) covers the `X-Request-Id` header on every response.
- [Interrupted call recovery](./interrupted-call-merge.md) covers restart recovery of `running` AI call
  records into `failed(interrupted)` with a `call` event.
