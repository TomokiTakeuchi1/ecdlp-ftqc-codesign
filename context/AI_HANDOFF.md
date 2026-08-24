# AI handoff

Last updated: 2026-08-24
From: claude
To: human and codex

## Current objective

All ten Codex submissions to date are Claude-reviewed and `APPROVED`. `T-20260824-002` adds the requested width-4 artifact for the reviewed processor-resident adaptive PBC lowering: complete JSON, a readable operation table, summary, and reproducibility record. Native backend timing remains deliberately unresolved. The separate Bell-bridge teleportation cycle remains approved but is not yet integrated into this adaptive PBC artifact.

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
- `docs/TELEPORTATION_BRIDGE_RIPPLE_CONTRACT.md`
- `experiments/runs/T-20260824-001/summary.json`
- `coordination/reviews/T-20260824-001.md`
- `experiments/runs/T-20260824-002/summary.json`
- `coordination/reviews/T-20260824-002.md`

## Next concrete action

1. Start a QCLA source/event-contract cycle that preserves prefix-tree dependencies before selecting a backend.
2. Human records the `T-BOOT-001` full-ECDLP choice; this remains the human-owned blocker before project-wide `T-BOOT-002` can be claimed.
3. Pin finite HGP/J300 bridge preparation, measurement, routing, and reaction costs, or begin memory/bridge co-scheduling, to move the Bell-bridge cycle from a normalized sensitivity toward an executable backend.

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
- The bridge-adder basis projection checks computational-basis carry semantics but is not a full coherent phase proof. Only the generic Bell bridge has an independent branchwise quantum-channel check in this cycle.
- The exact-ten bridge schedule is a normalized compatibility sensitivity. It does not encode J300 scratch allocation or an HGP-to-J300 physical layout, and strict mode rejects every generated finite schedule.
- The width-32 resource-state peak of 30 assumes ideal time-stamped supply and omits factory buffers, retries, routing, and stalls.
- The sibling source checkout advanced from the original Gidney fixture commit `8c16388` to `75a6e83`. Relevant Gidney/oracle paths are unchanged (independently reconfirmed during review via a direct empty `git diff` on the relevant source paths), but two older integration tests still demand exact checkout equality and fail in the current environment.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; all tasks' locks are now `RELEASED`.
