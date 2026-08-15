# Project status

Last updated: 2026-08-15
Owner: human
Phase: canonical baseline selection

## Current state

- Research scope has been defined at a high level.
- The first implementation target is a cross-layer trace and scheduler framework.
- No full ECDLP or QEC-backend baseline has yet been declared reproduced in this repository.
- Primary-source decision support recommends Schrottenloher 2026 as the first source baseline and Luo et al. 2026 v2 as a dynamic-circuit contrast.
- `RV-20260811-001` is `APPROVED` (Claude review, 2026-08-15). The recommendation itself does not close human-owned `T-BOOT-001`; the human decision recorded in `docs/CANONICAL_CIRCUIT_DECISION.md` is still required.
- The local source corpus now indexes 14 verified PDFs, including Gidney ripple addition, Draper et al. QCLA, the Babbush et al. and Chevignard et al. ECDLP estimates, and Kim et al. depth-oriented ECDLP circuits. `RV-20260811-002` is `APPROVED` (Claude review, 2026-08-15), including 3-of-14 sources spot-verified directly against arXiv.
- `T-20260815-001` implements a bounded Month-1 Gidney arithmetic prototype: pinned oracle schema v3 -> QEC-neutral DAG schema v1, explicit X-measurement/conditional-CZ feed-forward, widths 2--4 deterministic fixtures, and a width-256 structural regression. `RV-20260815-003` is `APPROVED` (Claude review, 2026-08-15; hand-traced width-2 fixture, reproduced 13/13 tests, ruff, and strict mypy). It does not close `T-BOOT-001` or project-wide `T-BOOT-002`. The review noted one non-blocking documentation suggestion for `docs/GIDNEY_DAG_CONTRACT.md` about erase-split memory/occupancy duplication, relevant when `T-BOOT-005` is implemented.

## Current milestone

Create a minimal reproducible pipeline:

1. ingest or generate one reference ECDLP arithmetic circuit;
2. emit a typed dependency and metadata trace;
3. schedule it on a sequential-PPM baseline backend;
4. reproduce a published or independently checked resource estimate;
5. add parallel-operation, memory-I/O, and factory constraints one at a time.

For the bounded Gidney arithmetic prototype, items 1 and 2 now have an
implemented candidate and local regression evidence. Sequential PPM
reproduction and QEC-native scheduling remain later tasks.

## Active bottleneck

Human selection of the exact circuit semantics and trace scope. The recommended primary circuit uses approximate arithmetic with random-input failure semantics; the exact low-space alternative has unresolved exceptional-point and count-contract checks.

## Next human decision

Choose between the two contracts in `docs/CANONICAL_CIRCUIT_DECISION.md`: accept the recommended Schrottenloher primary baseline, or require exact arithmetic and promote Luo v2 after resolving its documented checks.
