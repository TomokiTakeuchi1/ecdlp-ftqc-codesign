# AI handoff

Last updated: 2026-08-23
From: claude
To: human and codex

## Current objective

All eight Codex submissions to date are now Claude-reviewed and `APPROVED`, including `T-20260823-001` (`RV-20260823-001`): a source-pinned, replayable memory-I/O overlay. It reproduces the exact width-2--4 partition references and adds a fixed-event-order adaptive-PBC I/O sensitivity. Memory transfer timing, prefetch/overlap, Bell carry teleportation, QCLA, and factory stalls remain unresolved.

## Read first

- `context/PROJECT_CHARTER.md`
- `Research Hub/Home.md`
- `context/STATUS.md`
- `context/TASKS.md`
- `coordination/PROTOCOL.md`
- `docs/CANONICAL_CIRCUIT_DECISION.md`
- `coordination/reviews/T-20260811-001.md`
- `literature/papers/INDEX.md`
- `literature/READING_QUEUE.md`
- `coordination/reviews/T-20260811-002.md`
- `docs/GIDNEY_DAG_CONTRACT.md`
- `coordination/reviews/T-20260815-001.md`
- `docs/MITTEN_GIDNEY_LOWERING_CONTRACT.md`
- `coordination/reviews/T-20260815-002.md`
- `experiments/runs/T-20260815-002/summary.json`
- `docs/PBC_CQLU_LOWERING_CONTRACT.md`
- `experiments/runs/T-20260815-004/summary.json`
- `coordination/reviews/T-20260815-004.md`
- `docs/J300_PBC_SCHEDULING_CONTRACT.md`
- `experiments/runs/T-20260815-005/summary.json`
- `coordination/reviews/T-20260815-005.md`
- `docs/MEMORY_IO_EXECUTION_CONTRACT.md`
- `docs/RUNTIME_METADATA_IMPORT_MANIFEST.md`
- `experiments/runs/T-20260823-001/summary.json`
- `coordination/reviews/T-20260823-001.md`

## Next concrete action

1. Begin a separately scoped teleportation-based ripple-carry cycle using distinct Bell-bridge communication events; do not reuse memory-transfer timing as Bell-bridge timing.
2. Human records the `T-BOOT-001` full-ECDLP choice; this remains the human-owned blocker before project-wide `T-BOOT-002` can be claimed.
3. QCLA follows after its event and dependency contract is source-pinned.

The documentation follow-up repeated across `RV-20260815-004` and `RV-20260815-006` (citing `runtime_metadata_benchmark.gidney.coherent._apply_figure3_compute`/`verify_coherent_adder` in `docs/MITTEN_GIDNEY_LOWERING_CONTRACT.md`) is now done; Claude applied it directly after the second review, since it was a pure documentation addition with no implementation or scope change.

## Known risks

- Circuit conventions may differ across papers and codebases.
- Schrottenloher's primary candidate is approximate and its fast test is not full gate-level simulation.
- Luo v2 contains an internal `2^30.88` versus `2^30.63` full-count inconsistency; Table 6 plus Equation (8) supports `2^30.88` (independently reconfirmed during review).
- Neither artifact's local tests completed within the bounded verification window, so no published count is marked reproduced.
- The newly registered qLDPC/qLTC papers are only abstract-triaged; finite-size code, gadget, decoder, hardware, and factory assumptions are not yet normalized.
- Gidney now has a reviewer-reproduced width-256 structural DAG regression, but no QEC-native lowering, processor partition, or runtime result. QCLA remains a source-level candidate; Kim et al. 2026/106 is only abstract-triaged.
- The old J300 schedule is a `CHECK` sensitivity result, not a QEC-native runtime. The now-approved adaptive PBC trace removes the semantic CNOT/H/S/T blocker (verified correct via independent formula re-derivation and gadget-level Clifford-conjugation checks) but still lacks native preparation, Z/ZZ/ZX, reaction, conditional-CZ, setup/readout, and reconfiguration costs.
- The adaptive trace exposes many XX measurements, but widths 2/4/16/32 produce zero exact-ten hits under the implemented greedy readiness, scratch, operation-zone, and support constraints. This does not prove no alternative circuit rewrite or globally optimal scheduler can expose a batch; a synthetic ten-independent-CNOT witness confirms the batching code path itself is correct, isolating this as a workload/greedy-scheduler finding.
- One literature micro-claim in `docs/J300_PBC_SCHEDULING_CONTRACT.md` (Bhardwaj et al.'s Z-basis result being for J500 rather than J300) could not be independently verified during review because the local source PDF is unexpectedly password-protected; the caution is conservative-by-construction (it can only under-label evidence, never over-claim it) so this does not block acceptance, but a future session with a readable copy of the PDF should confirm it directly.
- Logical parallelism may be overestimated if conflicts and routing are omitted.
- Average factory rate may hide burst-induced stalls.
- The Obsidian dashboard is manually curated and can drift unless canonical records are updated first and the linked maintenance checklist is followed; four spots drifted one review-cycle behind within this same session and were resynchronized during `RV-20260815-005`.
- Memory traffic can dominate a small-processor architecture; see the erase-split occupancy-duplication note above for a concrete case to watch when `T-BOOT-005` is implemented.
- The new I/O/PBC result fixes the reviewed PBC event order before placement and forbids prefetch/compute overlap. Its width-32 100-load/100-store observation may change under a joint scheduler and is not a lower bound.
- The sibling source checkout advanced from the original Gidney fixture commit `8c16388` to `75a6e83`. Relevant Gidney/oracle paths are unchanged (independently reconfirmed during review via a direct empty `git diff` on the relevant source paths), but two older integration tests still demand exact checkout equality and fail in the current environment.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; all tasks' locks are now `RELEASED`.
