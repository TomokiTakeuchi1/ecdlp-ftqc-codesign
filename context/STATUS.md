# Project status

Last updated: 2026-08-23 (claude)
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
- `T-20260815-002` adds a phase-exact Figure-3 Clifford+T trace, an audited `[[300,60,14]]` Mitten configuration, strict rejection of unresolved native lowering, and a deterministic provisional greedy scheduler. `RV-20260815-004` is `APPROVED` (Claude review, 2026-08-15); the reviewer independently confirmed the Figure-3 gate sequence is an exact, gate-for-gate match to the pinned source's own exhaustively-verified `_apply_figure3_compute`, so the `NUMERICAL` label on primitive counts is substantively earned rather than merely inherited. The generated width-59 sensitivity point is 15,270 syndrome rounds with zero high-rate hits under `CHECK` placeholder costs; it is not an executable-runtime claim. Width 60 is rejected because source-recorded occupancy is 61, but PBC ancilla may lower the eventual executable width boundary. The review noted one non-blocking documentation suggestion for `docs/MITTEN_GIDNEY_LOWERING_CONTRACT.md` to cite that cross-check explicitly.
- `T-20260815-003` adds a plugin-free Obsidian Research Hub over the canonical project records. `RV-20260815-005` is `APPROVED` (Claude review, 2026-08-15); all navigation links, the Architecture Canvas, and evidence qualifiers were verified, and the reviewer synchronized four now-stale "in review" statuses to "reviewed" after approving `RV-20260815-004` earlier in the same session. The dashboard remains a manually curated presentation layer, not a replacement for `context/`, `coordination/`, or generated experiment records.
- `T-20260815-004` adds a quantum-output-preserving adaptive Pauli-measurement trace for CNOT/H/S/T/T-dagger, explicit compiler carriers and frame dependencies, and seeded branchwise channel checks with maximum Frobenius error `9.59372693274921e-16` (`NUMERICAL`). `RV-20260815-006` is `APPROVED` (Claude review, 2026-08-15); the reviewer independently re-derived all four generated-identity formulas (`113n-131`, `53n-62`, `20n-23`, `4n-4`) from the gadget structure and hand-verified the CNOT/H/S/T/T-dagger correction logic against the channel-verification code's Clifford-conjugation algebra, confirming the near-machine-precision error reflects a genuinely exact implementation rather than a coincidental match. One serialized reusable scratch changes the J300 slot-count boundary: width 58 uses 60 slots, while width 59 needs 61. This is not a strict runtime; preparation, Z/ZZ/ZX, reaction, conditional-CZ, and adaptive scheduling remain `CHECK`. The review repeated the earlier non-blocking suggestion to cite `runtime_metadata_benchmark.gidney.coherent._apply_figure3_compute` explicitly in `docs/MITTEN_GIDNEY_LOWERING_CONTRACT.md`.
- `T-20260815-005` maps the reviewed adaptive trace to an evidence-qualified J300 schedule. `RV-20260815-007` is `APPROVED` (Claude review, 2026-08-15); the reviewer hand-verified the 550-to-433-round high-rate savings (117 rounds = 10x13 seed operations minus 1x13 batched operation, exactly), traced the scratch-slot allocation/release logic for correctness, and confirmed the "zero high-rate hits" result is a workload/greedy-scheduler finding (confirmed by the synthetic ten-CNOT witness) rather than an impossibility claim. Timing and added-space evidence are separate; strict mode rejects unresolved preparation, Z/ZZ/ZX/full-extractor timing, reaction, and conditional-CZ claims. Under the `CHECK` sensitivity profile, widths 2/4/16/32 schedule in 846/2,868/15,000/31,176 rounds on one operation zone and expose zero eligible ten-XX batches even with ten scratch slots. The 2,074 physical-qubit value is an incomplete known-component peak, not a total machine count. The review disclosed one unverifiable literature micro-claim (whether a cited Z-basis result was J500 vs. J300) that is conservative-by-construction and does not affect any conclusion.
- `T-20260823-001` is a source-pinned memory-I/O overlay porting value-origin, maximal-prefix partition, fixed-order Belady, and independent replay contracts from `runtime-metadata-benchmark` commit `75a6e83d5acde37f0987ab867352ee8b2c6afd10`. It reproduces all admitted width-2--4 exact partition references. A fixed-event-order adaptive-PBC overlay preserves the reviewed schedule at zero transfer latency and, under a one-lane/one-round `CHECK` sensitivity profile, changes widths 2/4/16/32 from 846/2,868/15,000/31,176 to 854/2,884/15,064/31,376 rounds. Width 32 uses 100 loads and 100 stores under this order/policy; this is not a lower bound or QEC-native runtime. `RV-20260823-001` is `APPROVED` (Claude review, 2026-08-23); the reviewer independently reproduced the empty diff between the two pinned sibling-repository commits (confirming the two stale-HEAD test failures are a pin-staleness artifact, not a regression), hand-traced the erase-split memory/occupancy union fix that resolves a concern raised in an earlier review, and confirmed `replay.py` performs genuine from-scratch independent verification rather than re-checking the placement algorithm's own bookkeeping.

## Current milestone

Create a minimal reproducible pipeline:

1. ingest or generate one reference ECDLP arithmetic circuit;
2. emit a typed dependency and metadata trace;
3. schedule it on a sequential-PPM baseline backend;
4. reproduce a published or independently checked resource estimate;
5. add parallel-operation, memory-I/O, and factory constraints one at a time.

For the bounded Gidney arithmetic prototype, items 1 and 2 now have an
implemented candidate and local regression evidence. A first conditional
Mitten scheduler exists and the explicit, phase-verified Pauli-based
compilation is now reviewed and approved. A reviewed adaptive resource
scheduler now exists as a sensitivity model, but strict QEC-native runtime
still awaits source-pinned native preparation, Z/ZZ/ZX, reaction, and
conditional-CZ contracts.

The bounded Gidney pipeline now also has a replayable processor-memory I/O
overlay. Its transfer timing remains `CHECK`, and joint optimization of
parallel circuit order with placement is not yet implemented.

## Active bottleneck

Human selection of the exact circuit semantics and trace scope. The recommended primary circuit uses approximate arithmetic with random-input failure semantics; the exact low-space alternative has unresolved exceptional-point and count-contract checks.

## Next human decision

Choose between the two contracts in `docs/CANONICAL_CIRCUIT_DECISION.md`: accept the recommended Schrottenloher primary baseline, or require exact arithmetic and promote Luo v2 after resolving its documented checks.
