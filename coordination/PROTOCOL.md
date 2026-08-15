# Codex窶鼎laude coordination protocol

This protocol provides procedural cross-monitoring. It does not run either agent as an unattended background service.

## 1. Before work

1. Pull or inspect the latest repository state.
2. Read the shared context.
3. Check the review queue.
4. If the other agent has submitted work, review it first unless a human set another priority.
5. Claim one task in `context/TASKS.md`.
6. Add a row to `coordination/WORK_LOCKS.md` listing the intended files.
7. Create a session record from `templates/SESSION_TEMPLATE.md`.

## 2. During work

- Do not modify files locked by another owner.
- Record newly discovered scientific assumptions in `context/ASSUMPTIONS.md`.
- Record durable design choices in `context/DECISIONS.md`.
- Prefer a new small module over a broad refactor.
- Keep generated data outside source directories.

## 3. Submit for review

Create a review file from `templates/REVIEW_TEMPLATE.md`, then add one row to `coordination/REVIEW_QUEUE.md`.

The submission must contain:

- task ID and owner;
- branch and commit, if available;
- changed files;
- scientific claim or software behavior;
- assumptions;
- tests and commands run;
- expected reviewer focus;
- known limitations.

## 4. Review

The other agent independently checks the diff, tests, units, assumptions, and reproducibility.

Review outcomes:

- `APPROVED`
- `CHANGES_REQUESTED`
- `BLOCKED_BY_SCIENTIFIC_DECISION`
- `INCONCLUSIVE`

Only a human resolves a disputed research interpretation unless an authoritative source or proof settles it.

## 5. Finish

- Update the task status.
- Update `context/STATUS.md`, `context/RESULT_LEDGER.md`, and `context/AI_HANDOFF.md` when relevant.
- Remove or mark the lock released.
- Preserve the session and review records.

## Conflict rule

When both agents propose different implementations, retain both proposals long enough to compare them with the same tests or benchmark. Do not silently select one by overwriting the other.