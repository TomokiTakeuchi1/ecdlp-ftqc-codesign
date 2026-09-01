# AI handoff

Last updated: 2026-09-01
From: claude
To: codex and human

## Next high-rate-aware QCLA-to-PPM cycle

`T-20260901-006` is `RV-20260901-005` `APPROVED` (Claude review, 2026-09-01).
The reviewed OOP-QCLA `n=5` source now lowers directly, without seven-T
decomposition, through the exact `|CCZ>` injection event into a canonical
symbolic PPM/frame trace. The 23 source operations produce ten injections, 60
PPMs, 60 conditional frame updates, and thirteen implementation-neutral CNOTs
while preserving 36 source dependencies, sixteen source logical lifetimes, ten
CCZ resource lifetimes, and zero compiler ancillas. The independent serialized
replay checks 640 local correction rows, 23 frame transitions, 3,840 presented
observables on 64 deterministic global probes, all 1,024 basis inputs, and the
all-64-branch local injection channel with zero operator residual. The
reviewer independently verified every primitive Clifford-conjugation rule
(H/X/Z/CNOT/CZ) against explicit unitary matrices, recognized the CNOT phase
formula as the textbook Aaronson-Gottesman stabilizer sign-update rule, and
performed an independent end-to-end reconstruction of a nontrivial later
PPM's presented observable -- catching and fixing a bug in the reviewer's own
first attempt (a missed passthrough-CNOT frame-reconjugation replay step)
before confirming an exact match with the compiler's stored output. See
`docs/DIRECT_CCZ_PPM_TRACE_CONTRACT.md` and
`coordination/reviews/T-20260901-006.md` for the complete finding list.

This is a `NUMERICAL` semantic trace, not a native schedule or formal proof.
The global probes are not exhaustive `2^60` enumeration, source layers are not
surgery rounds, and pass-through CNOT time/space/routing/memory costs remain
`OPEN`. Both compiler and replay reject `complete_native_schedule=true`; no
`schedule.json` was emitted.

`T-20260901-007` is now `READY` and must optimize batches while keeping three
outputs separate: general high-rate candidates, finite-instance-admitted
operations, and low-rate fallback. `T-20260901-008` renders those decisions from the same
machine-readable trace. `T-20260901-009` reuses the compiler for IP-QCLA
without the existing seven-T route. `T-20260901-010` is the first point at
which width scaling and a compatible finite backend may be integrated.

The cycle contract is
`docs/HIGH_RATE_QCLA_PPM_OPTIMIZATION_CYCLE.md`. It explicitly forbids
treating source Toffoli layers, pairwise commutation, logical-axis consistency,
or noiseless Gross-code observations as an executable high-rate runtime.
Runtime additionally requires memory, routing, reaction, decoder, CCZ
factory/buffer, physical-space, and failure-budget fields from one compatible
backend.

## Current objective

`T-20260901-001` is `RV-20260901-001` `APPROVED` (Claude review, 2026-09-01).
Gidney--Fowler Figures 3--6 plus the official layouts connect one CCZ factory
output to a three-delayed-CZ AutoCCZ fixup box and one Toffoli consumer in a
single surface-code domain. An independent abstract channel check finds all 64
branches at probability `1/64`, maximum probability error
`2.2551405187698492e-17`, and zero ideal-CCX operator residual. The adapter is
admitted, but complete service remains false: nine finite fields are missing,
and the official `5.33332e-11` calculator error belongs to `d1=15,d2=31`, not
the selected AutoCCZ `d1=17,d2=27` example. Under explicitly `CHECK` timing
inputs, the latter yields 135 cycles/CCZ, approximately 7.407 kHz per factory,
and fourteen factories for 100 kHz average demand. No schedule was emitted.
The reviewer rendered the primary PDF's Figures 3, 4, and 6 directly at 300
DPI and confirmed the delayed-choice-cell abstraction, three-cell/six-routing
-qubit structure, and one-port consumer interface are faithfully transcribed,
with `pdftotext` independently matching the paper's own worked-example
arithmetic word-for-word; separately unzipped and parsed the official ODS
calculator's raw XML and found the `5.33332e-11` cell's own formula is in the
same column as `d1=15`, with `d1=17` never appearing anywhere in the sheet --
directly and independently settling the calculator-incompatibility claim from
the spreadsheet's own structure rather than the doc's description of it. See
`coordination/reviews/T-20260901-001.md` for the complete finding list.

`T-20260831-004` is `RV-20260831-004` `APPROVED` (Claude review, 2026-08-31).
The fail-closed audit covers 17 required direct-CCZ fields and screens seven
pinned primary sources without composing incompatible code families. The
selected Cain ECC-256 `P=20` time-efficient candidate is rejected: 13 finite
service fields remain absent, while the only qualified factory batch size,
production time, and output-error values belong to the separate `bb18`
space/balanced domain. The portable Figure 14(a) event remains admitted. No
schedule artifact was emitted. The reviewer independently re-hashed all seven
source PDFs, confirmed the `_PORTABLE_FIELD_IDS` exemption is a hardcoded
Python constant rather than a YAML-editable field, ran every boundary test
(forged admission, omitted field, coherent synthetic admission, mixed-domain
rejection, real-candidate rejection), and -- most importantly -- pulled the
raw Cain PDF text at pages 19 and 24 and found the source itself states the
10-CCZ/120-cycle/`1e-10` figures apply "in our space-efficient or balanced
architecture" (a different regime from the selected `P=20` time-efficient
candidate) and that the time-efficient appendix explicitly disclaims
specifying "concrete circuits or instruction sets." See
`docs/DIRECT_CCZ_FINITE_BACKEND_AUDIT.md`,
`configs/architectures/direct_ccz_finite_backend_audit_v1.yaml`,
`experiments/runs/T-20260831-004/summary.json`, and
`coordination/reviews/T-20260831-004.md` for the complete finding list.

`T-20260831-003` implementation commit `75effd5` is `RV-20260831-003`
`APPROVED` (Claude review, 2026-08-31). Litinski--Nickerson Figure 14(a) now
supplies the exact single-event conditional-CZ/post-H Pauli map under the
explicit measurement convention `0 -> +1`, `1 -> -1`. A verifier that imports
neither the capability nor compiler reconstructs the six-qubit projector
channel and finds all 64 branches nonzero at probability `1/64`, with maximum
probability error `2.2551405187698492e-17` and zero operator Frobenius
residual at floating-point precision. The real capability therefore admits
isolated event lowering. The reviewer independently confirmed this by
rendering the primary source PDF page to a 600 DPI image and directly
pixel-verifying every wire assignment, conditional-CZ pairing, and final
Pauli-correction formula in Figure 14(a) against the machine-encoded map
(zero discrepancies), and by writing a separate from-scratch numpy channel
reconstruction from the contract's prose alone (before reading the
repository's own verifier), which independently reproduced all 64 nonzero
branches at matching precision; see `coordination/reviews/T-20260831-003.md`
for the complete finding list.

The width-256 clean OOP-QCLA lowers to 1,229 direct-CCZ injection events,
7,374 PPM/outcome records, 3,955 preserved source dependencies, and 766
pass-through CNOTs. Event-trace schema v2 explicitly remains
`complete_native_schedule=false`. High-rate admission remains false: finite
timing, error, decoder, reaction, port, capacity, routing, factory delivery,
buffer, and storage evidence is still absent. No runtime or physical-resource
result was created.

`T-20260831-002` completed the first bounded cycle proposed by the reviewed
direct-CCZ plan. It generated and replay-validated a clean out-of-place
modulo-\(2^{256}\) QCLA trace with 1,229 Toffolis, 766 CNOTs, 20 source layers,
240 clean prefix-scratch values, and 1,008 fully resident source values. These
are architecture-neutral circuit quantities, not runtime.

The same cycle audited the pinned direct-CCZ and high-rate sources into a
machine-readable capability record. The sources establish a six-PPM
single-injection skeleton and a separate ten-CCZ/120-cycle factory observation,
but not the exact outcome-to-correction map or a finite high-rate direct-CCZ
backend. The adapter therefore rejects before emitting any source-qualified
event. Implementation commit `deebfc4` is `RV-20260831-002` `APPROVED`
(Claude review, 2026-08-31). The reviewer wrote an independent from-scratch
classical-reversible simulator (bypassing the repository's own
`replay_oop_qcla`) and confirmed every closed-form count and the fail-closed
capability/adapter logic; see `coordination/reviews/T-20260831-002.md` for
the complete finding list. The `OPEN` capability conclusion itself is
unchanged by the review -- the exact correction map and finite high-rate
backend remain absent from the literature.

`T-20260825-002` converted the reviewed width-256 QCLA adaptive-PBC trace from
a resident-capacity rejection into an independently replayed, fixed-order
60-slot J300 memory schedule. The width-256 ten-scratch high-rate policy
selects 1,576 exact-ten-XX batches. Under the explicitly `CHECK`
one-lane/one-round/no-overlap profile it takes 2,420,527 rounds, 169,260
(6.54%) below one-scratch serial despite 7,433 more reloads. This is not
executable time. The complete shifted T-demand trace sums to 17,206 but has
no factory service, buffer, routing, or stalls.

## Incoming-collaborator orientation

`T-20260901-004` is `RV-20260901-003` `APPROVED` (Claude review, 2026-09-01).
`docs/HANDOFF.md` is a concise English entry note for an incoming
collaborator. It presents the one-week/order-`10^4`-qubit research target,
summarizes the teleportation-ripple HGP and QCLA/high-rate-surgery tracks,
lists their open physical-contract questions, and links scoped starting
references. It creates no numerical result or executable architecture claim.
The reviewer independently verified all ten citations against arXiv and the
local bibliography with no discrepancies found.

`T-20260901-003` is `RV-20260901-002` `APPROVED` (Claude review, 2026-09-01).
The two human-audit OOP-QCLA `n=5` figures (source circuit and direct-CCZ
injection expansion) live outside the git repository in a thread-owned
visualization cache; see `coordination/reviews/T-20260901-003.md` for their
path. The reviewer independently regenerated the width-5 trace and matched
all 23 gates and the displayed correction formula exactly.

## Read first

- `context/PROJECT_CHARTER.md`
- `Research Hub/Home.md`
- `context/STATUS.md`
- `context/TASKS.md`
- `coordination/PROTOCOL.md`
- `coordination/reviews/T-20260901-001.md`
- `docs/AUTOCCZ_SURFACE_CODE_ADAPTER.md`
- `configs/architectures/autoccz_surface_code_adapter_v1.yaml`
- `experiments/runs/T-20260901-001/summary.json`
- `experiments/runs/T-20260901-001/autoccz_service_audit.json`
- `experiments/runs/T-20260901-001/autoccz_channel_verification.json`
- `coordination/reviews/T-20260831-003.md`
- `docs/DIRECT_CCZ_SINGLE_EVENT_CONTRACT.md`
- `configs/architectures/direct_ccz_single_event_capability_v1.yaml`
- `experiments/runs/T-20260831-003/summary.json`
- `experiments/runs/T-20260831-003/direct_ccz_injection_channel_verification.json`
- `coordination/reviews/T-20260831-002.md`
- `docs/DIRECT_CCZ_CAPABILITY_AND_OOP_QCLA_CONTRACT.md`
- `configs/architectures/direct_ccz_high_rate_capability_v1.yaml`
- `experiments/runs/T-20260831-002/summary.json`
- `experiments/runs/T-20260831-002/direct_ccz_capability_gap.json`
- `coordination/reviews/T-20260825-002.md`
- `docs/QCLA_MEMORY_IO_CONTRACT.md`
- `docs/QCLA_PBC_LOWERING_CONTRACT.md`
- `configs/architectures/qcla_j300_memory_io_v1.yaml`
- `experiments/runs/T-20260825-002/summary.json`
- `experiments/runs/T-20260825-002/qcla_width256_t_state_demand.json`
- `context/RESULT_LEDGER.md`
- `docs/HIGH_RATE_QCLA_DIRECT_CCZ_RESEARCH_CYCLE.md`
- `coordination/reviews/T-20260831-001.md`

## Next concrete action

1. Implement `T-20260901-007`: classify and optimize the width-5 trace
   while reporting general high-rate candidates, finite-instance admission,
   and low-rate fallback separately.
2. Source or compute a `d1=17,d2=27` output/transport/consumer
   error model and a finite decoded buffer/reaction contract before connecting
   the AutoCCZ adapter to width-256 QCLA demand.
3. Add factory service, finite buffer, routing, and backlog to the width-256
   adaptive-PBC T-demand series as a separate, comparison track; report stalls
   separately from the current ideal-supply timeline.
4. Human records the `T-BOOT-001` full-ECDLP circuit choice before project-wide
   `T-BOOT-002` is claimed.

## Known risks

- `R-20260901-003` preserves exact ANF conditions, but its 64 global outcome
  probes are a regression set rather than exhaustive `2^60` branch coverage.
  The local injection itself remains all-64-branch checked.
- Assumption `A-0035` propagates source CNOTs semantically as materialized
  Clifford frames and assigns no finite native cost. Phase B must not turn
  these frame records into zero-time physical operations.
- `R-20260901-001` is an abstract logical-channel reconstruction whose
  delayed-choice CZ cells are accepted from the paper; it does not simulate
  surface-code faults or independently validate the 3D layout.
- `R-20260901-002` uses source-stated cycle/reaction inputs as `CHECK`; average
  throughput and fourteen-factory arithmetic do not prove burst service.
- The official workbook's finite output error is deliberately incompatible
  with the selected distances. Substituting it would create a false closed
  failure budget.
- `R-20260831-006` is an `OPEN` negative admission result. Its field counts are
  deterministic, but they do not prove that no finite direct-CCZ backend can
  exist; they prove only that the pinned corpus does not close the selected
  candidate under the recorded compatibility rule.
- Tricycle finite CCZ generation strengthens the factory side but leaves
  selective initialization and target-code teleportation unresolved; the
  reported low memory error does not include the CCZ circuit's contribution to
  final magic-state fidelity.
- The clean QCLA source-ancilla allocation/release boundaries are validated
  from source reuse epochs, but their physical preparation/reset/routing time
  remains `CHECK` and adds no separate duration in this cycle.
- The capacity-relaxed adaptive-PBC pass selects an order only. The second pass
  enforces 60 slots, but the order and Belady retention are heuristic and are
  neither optimal nor lower bounds.
- Transfer prefetch/overlap, finite memory capacity, routing, bridge occupancy,
  decoder throughput, logical failure, and wall-clock conversion are absent.
- The QCLA is uncontrolled in-place addition modulo `2^n`, without carry-in or
  overflow; it is not yet the controlled arithmetic needed by scalar
  multiplication.
- Direct CCZ injection may dominate the seven-T baseline in space or time.
- The high-rate source presently supports a finite XX PPM demonstration, not an admitted direct-CCZ batch; this is an explicit input gap, not a scaling assumption.
- The clean OOP trace is validated on computational-basis replay and structural identities; it is not an independent coherent-phase proof of the full arithmetic circuit.
- The legacy T-20260831-002 capability record intentionally remains null and fail-closed. Only the new Figure-14-qualified configuration admits isolated events.
- The branch reconstruction is `NUMERICAL`, not a formal proof, and it does not establish any finite high-rate architecture.
- Cain's three-surgery-cycle parallel model is stored as a `CHECK` assumption, not an admitted finite duration or instruction set.
- The older Gidney integration suite retains two known checkout-pin failures:
  expected sibling HEAD `8c16388`, observed `75a6e83`. The relevant source
  paths were reviewed as identical; this QCLA task does not use that checkout.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; `T-20260901-006` is `RELEASED` (reviewed and approved). No task currently holds an active `REVIEW`/`ACTIVE` lock; `T-20260901-007` is `READY` to be claimed.
