# Shared instructions for Codex, Claude Code, and human contributors

## Project mission

Build a reproducible cross-layer framework for ECDLP-256 Shor resource estimation. The framework must connect algorithmic dependency structure to concrete FTQC constraints rather than relying only on logical-qubit counts, T/Toffoli counts, or idealized depth.

## Mandatory startup procedure

Before editing anything:

1. Read `context/PROJECT_CHARTER.md`.
2. Read `context/STATUS.md`, `context/TASKS.md`, and `context/AI_HANDOFF.md`.
3. Read `context/CONVENTIONS.md` and `coordination/PROTOCOL.md`.
4. Inspect `coordination/WORK_LOCKS.md` and `coordination/REVIEW_QUEUE.md`.
5. Review pending work from the other agent before claiming a new implementation task, unless a human explicitly prioritizes otherwise.
6. Claim exactly one task and record the claim before modifying project files.

## Agent identity

When writing coordination records, use exactly one owner label:

- `codex`
- `claude`
- `human`

Do not impersonate the other agent. Do not silently overwrite the other agent's changes.

## Branch and task discipline

- Use task IDs of the form `T-YYYYMMDD-NNN`.
- Preferred branch format: `agent/<owner>/<task-id>-<short-slug>`.
- One task must have one primary implementer.
- The implementer must list the files or directories it expects to modify in `coordination/WORK_LOCKS.md`.
- Do not concurrently edit a locked file. Put suggestions in the corresponding inbox or review file instead.
- Keep commits small and describe scientific as well as software consequences.
- Never perform destructive cleanup, history rewriting, or broad refactoring without an explicit task.

## Cross-review protocol

Every nontrivial implementation by Codex should be reviewed by Claude, and vice versa.

The implementer must:

1. run the relevant tests and validation commands;
2. update the task/session record;
3. add an item to `coordination/REVIEW_QUEUE.md` assigned to the other agent;
4. state assumptions, changed files, tests, known limitations, and the commit hash if available.

The reviewer must check:

- correctness of the dependency model and units;
- whether algorithmic parallelism is confused with executable architecture parallelism;
- memory load/store accounting;
- factory throughput, burst demand, and buffering assumptions;
- logical error and failure-budget assumptions;
- deterministic reproducibility of numerical results;
- regression tests and boundary cases;
- whether claims are stronger than the evidence.

A reviewer should not rewrite the implementation while reviewing unless the task is explicitly reassigned. Record requested changes in the review file.

## Scientific evidence labels

Use only these labels in research records:

- `PROVED`
- `NUMERICAL`
- `LITERATURE`
- `CONJECTURE`
- `OPEN`
- `CHECK`
- `FALSIFIED`
- `INCONCLUSIVE`

Every important claim must have one label. Never present a numerical observation as a proof.

## Reproducibility rules

Every numerical result must identify:

- task ID;
- git commit or working-tree state;
- input circuit or trace;
- configuration file;
- code and architecture assumptions;
- random seed, when applicable;
- software environment;
- output path;
- validation status.

Do not manually edit generated result files. Change the source, configuration, or generator and rerun it.

## Research-domain rules

- Separate algorithmic critical path from resource-constrained scheduled depth.
- Separate processor capacity, operation throughput, cycle time, and total processing capacity.
- Treat memory bandwidth, load/store latency, decoding, classical reaction time, routing, and factory supply as explicit resources.
- Model magic/resource-state demand as a time series, not only an average rate.
- Keep lower bounds, heuristic schedules, and realizable upper bounds clearly separated.
- Record the precise logical instruction semantics and Pauli support.
- Do not assume a code supports arbitrary parallel PPMs unless the construction and constraints are explicitly encoded.
- Do not assume a factory can sustain peak consumption without a buffer and routing model.

## Coding rules

- Target Python 3.11 or later unless `context/DECISIONS.md` changes this decision.
- Use type hints for public functions.
- Prefer immutable data models for configuration and trace records.
- Validate external inputs at module boundaries.
- Keep architecture-independent circuit semantics separate from backend scheduling.
- Add a regression test whenever fixing a bug.
- Avoid notebooks for canonical logic; notebooks may call library code for analysis and visualization.

## Completion procedure

Before ending a work session:

1. run tests or explain exactly why they could not be run;
2. update `context/STATUS.md` if project-level state changed;
3. update `context/DECISIONS.md` for durable decisions;
4. update `context/RESULT_LEDGER.md` for scientific results;
5. update `context/AI_HANDOFF.md` with the next concrete action;
6. update the task/session record;
7. release or refresh the work lock;
8. request cross-review when appropriate.