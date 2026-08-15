# Task board

Allowed statuses: `BACKLOG`, `READY`, `CLAIMED`, `IN_REVIEW`, `BLOCKED`, `DONE`, `CANCELLED`.

| ID | Priority | Status | Owner | Title | Dependencies | Acceptance criterion |
|---|---:|---|---|---|---|---|
| T-BOOT-001 | 0 | READY | human | Select canonical ECDLP-256 reference circuit | 窶・| Circuit source, version, conventions, and expected counts are recorded |
| T-BOOT-002 | 0 | READY | unassigned | Define circuit-trace and metadata schema | T-BOOT-001 | Versioned schema covers dependencies, support, roles, lifetimes, measurements, and classical conditions |
| T-BOOT-003 | 1 | BACKLOG | unassigned | Implement sequential PPM baseline scheduler | T-BOOT-002 | Regression test reproduces a hand-computed toy example |
| T-BOOT-004 | 1 | BACKLOG | unassigned | Implement ideal bounded-parallelism scheduler | T-BOOT-002 | Critical path and width constraints are separately testable |
| T-BOOT-005 | 1 | BACKLOG | unassigned | Implement processor-memory I/O model | T-BOOT-002 | Load/store counts are reproducible under a stated replacement policy |
| T-BOOT-006 | 1 | BACKLOG | unassigned | Implement time-dependent factory model | T-BOOT-002 | Reports demand trace, backlog, stalls, utilization, and buffer occupancy |
| T-BOOT-007 | 2 | BACKLOG | unassigned | Build literature assumption matrix | 窶・| Each cited estimate has explicit algorithm, code, timing, factory, and parallelism assumptions |
| T-BOOT-008 | 2 | BACKLOG | unassigned | Define failure-budget model | 窶・| Failure contributions and allocation rules are versioned and unit-tested |

| T-20260811-001 | 0 | DONE | codex | Prepare canonical ECDLP-256 circuit decision support | none | Primary-source comparison records exact source/version, available implementation artifacts, circuit scope and count conventions, then gives a qualified recommendation or an explicit decision blocker |
| T-20260811-002 | 1 | DONE | codex | Register user-specified FTQC literature corpus | none | User-specified arXiv and IACR ePrint references are deduplicated and version-pinned in local PDFs, bibliography metadata, reading queue entries, and structured triage notes |
| T-20260815-001 | 0 | DONE | codex | Adapt the verified Gidney oracle to a QEC-neutral causal DAG | none (bounded Month-1 arithmetic prototype; does not close T-BOOT-001 or T-BOOT-002) | A pinned Gidney oracle converts reproducibly into a versioned DAG with quantum, lifetime, measurement, and classical feed-forward dependencies; widths 2--4 pass semantic regressions and width 256 passes structural validation |

## Task update rule

Do not erase history. Change the status and add details in a session file under `coordination/sessions/`.
