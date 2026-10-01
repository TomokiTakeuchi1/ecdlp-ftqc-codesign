---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - progress
updated: 2026-10-01
---

# Research Progress Log

[[Research Hub/Home|← Home]] · [[Research Hub/Roadmap|Roadmap]] · [[Research Hub/Decisions and Blockers|Decisions & Blockers]]

This page explains the research in plain language. Evidence, assumptions, and exact counts live in the linked canonical records.

## 2026-10-01 - Completed-LP GHZ measurement interface (reviewed and approved)

T-20261001-001 reconstructs the finite 9,600-data-qubit LP code and its 300
four-logical-qubit resource lanes. Its source's Z-homology convention transposes
the advertised computational gate; the GHZ input is |000+>.

The explicit 525-qubit helper gives a code-preserving ideal measurement.
Raw302 includes two residual observables; strict300 uses two extra weight-75
checks. Both are unprotected against a single Z corrupting readout. This
isolates the next research problem as protected preparation/readout; it is not
a claim of a completed FT factory or fast arithmetic.
See [[docs/LP_GHZ_HOMOMORPHIC_PREPARATION_CONTRACT|construction and evidence]].

**Status:** Reviewed and approved (`T-20261001-001`, `RV-20261001-001`, 2026-10-01). Claude independently rebuilt the entire GF(2) code from scratch (different representation), matched every rank/dimension/commutation claim, reconstructed the canonical section via a different method, confirmed all 1,200 X/Z generators form an exact dual pairing, and derived by hand that the automorphism's X-orientation is mathematically forced (not a free choice) given the stated Z-orientation. The seed exponents' fidelity to the private PDF could not be checked (the PDF is not accessible to the reviewer).

## 2026-09-27 — H-tracked / bare-CNOT low-rate profile

**Status:** Reviewed and approved (`T-20260927-001`, `RV-20260927-001`, 2026-10-01). Claude recomputed all 66 artifacts' signed traces (Stim), grid cells, and comparisons with zero discrepancies, and reproduced every headline number.
claude. This fills the missing hybrid
between full tracking and conjugated-H/bare-CNOT.

NUMERICAL: on 64 hashed width-256 IP branches, unlimited-support K=64 median
surgery steps are hybrid/full 305/296 (QWC), 263/263 (general). General's four
service counts are identical branch by branch at all six K values. Bare-X
and virtual-X sensitivity have equal axes and service, not identical signs.
Both forced branches are retained separately, with no probability claim.

CHECK: the branch-paired additional CNOT/X budget median is -6 units for QWC
and zero for general at unlimited support. At S=512, general instead has a
median of 1 (range -8..11). Four native CNOT layers remain unknown service;
one call per layer is only a sensitivity. There is no demonstrated native win.

All 1,946,736 signed coupling PPMs across four policies were replayed; three
fresh artifacts are byte-identical. The old full/legacy traces and lowerings
match on all 66 branches, with 1,980 common service cells identical. Physical
qubits, native time, factory/routing, failure and endpoint materialization
remain OPEN. Full tests: 487 passed plus two known sibling-pin failures; latest
related tests: 107 passed (including five added after full-suite collection).
See [[docs/H_TRACKED_BARE_CNOT_LOW_RATE_CONTRACT|hybrid contract]].

## 2026-09-26 — Paired Clifford-budget comparison

**Status:** Reviewed and approved (`T-20260926-002`, `RV-20260926-002`, 2026-09-27). Claude recomputed every grid entry of all 580 artifacts, densely verified the legacy entrance-frame H/H semantics, and reproduced the selector, refined counts (218/179 of 512) and tables; the legacy Clifford cost B remains unknown.

The comparison now uses the same low-rate backend for both full tracking and
conjugated-H/bare-CNOT. It measures how much extra physical Clifford time the
latter can afford, rather than assuming those gates are free. Initial 64-hash
OOP/IP profiles are independently checked. The 18 IP/weight-256 boundary
cells were extended to 512 hashes under the predeclared selection rule:
legacy PPM fits 512, tracked QWC 218, fixed general lowering 179. Other cells
remain at 64 hashes. This is not a probability law or a universal ordering
of measurement constructions; Cliffords still need a realizable service B.
The versioned Zhang--Li and Cowtan et al. PDFs are pinned with SHA-256.

CHECK: at K=64 with unbounded support, median additional-Clifford budgets
against tracked QWC are 29 units (OOP) and 170 units (IP). These are total
kernel allowances, not time per H/CNOT or a complete hardware estimate.

Details: [[docs/LOW_RATE_CLIFFORD_BREAK_EVEN_CONTRACT|paired comparison contract]].

Post-review synchronization (codex, 2026-09-27): task DONE, review APPROVED,
D-0034 ACCEPTED; no required changes. Session, contract and handoff now agree
with the review. Implementation and numerical outputs are unchanged, and
legacy Clifford execution/native runtime remain OPEN.

Validation: 8,067,156 signed coupling PPM replays; seven fresh artifacts and
resumed summary/SVG byte-identical; independent exact-rational saved-output
audit and visual map QA. Full suite 454 pass plus two known sibling-pin
failures; latest focused + Hub 43 pass. No commit or native runtime claim.

## 2026-09-26 — Parallel low-rate surgery on fully tracked QCLA

**Status:** Reviewed and approved (`T-20260926-001`, `RV-20260926-001`, 2026-09-26)

What changed:

- Tracked every source H/CNOT in a signed Clifford frame (no physical gates), then lowered each reviewed CCZ macro into logical measurements two ways: *QWC* (measure compatible Paulis together) and *general* (change the generating set so every commuting set becomes two regular sets, each measured with a two-stage gadget on a fresh |0> ancilla).
- Applied capacity limits after lowering: K simultaneous measurements, per-measurement logical weight, and total support. 64 hashed plus two forced branches for each width-256 OOP and IP workload; 730,026 coupling measurements independently replayed.

Plain-language reading: with unlimited support, median surgery steps are OOP 92 (QWC) / 111 (general) and IP 296 / 263 at K=64, and OOP 54 / 44, IP 249 / 104 with unlimited K. Under an arbitrary CHECK service example (preparation, readout, reaction charged) the IP K=64 ordering reverses (330.5 versus 359.5 units), so fewer primary steps do not automatically mean less time. Tracked frames make logical weights large (IP median 261-270, all-one witness 638-662), so a cap of 512 admits every hashed witness but not the all-one witness.

Review notes (Claude): the signed traces were recomputed with an independent Clifford-tableau library (every measurement and final frame equal); multi-event macros and the measurement gadget were verified with from-scratch dense simulations; all 132 artifacts passed an independent regularity/packing audit and every table value was reproduced; the cited papers were read and match. Non-blocking: pin the two PDFs; executed maximum weight (not step count) shifts by about 10% under another valid regularization order.

Still open: physical representatives and weights, routing, native timing, decoder/reaction, factory/buffer service, memory, physical qubits, and failure. The 512-witness boundary refinement has not been run.

## 2026-09-26 — Partial Clifford-frame clearing (compiler profile)

**Status:** Reviewed and approved (`T-20260909-001`, `RV-20260909-001`, 2026-09-26)

What changed:

- Formalized every H-frame policy from one equation, `G = F_out U F_in^dagger`, under the byproduct convention `physical = F ideal`, and added *target-component partial clearing*: only the frame components touching a simultaneous H layer are materialized, disjoint components stay in the frame.
- Width 5: 11,520 exact projective Clifford checks, zero mismatch. On the coherent width-256 IP 30/60 workload with 32 fixed branch witnesses, partial clearing has median 3,843 literal CNOTs versus 4,250 for full clearing (9.58% fewer) but more serialized layers (380 versus 270) and wider presented PPM support (median 11, sampled maximum 16, versus 2).

Plain-language reading: clearing less of the frame saves gate occurrences but leaves a bigger frame behind and lengthens the same-wire ordering. This is a trade-off between three quantities, not a winner, and none of the numbers is time.

Review notes (Claude): the frame convention and factor order match the approved compiler; frame accumulation was cross-checked against the approved symbolic compiler on 192 width-5 rows, and all width-256 headlines were reproduced by a second implementation. The CNOT-batch envelope depends on ASAP direction (148/249 when scheduled forward in time versus the stored 176/284); the layer envelope is essentially invariant.

Still open: native H/CNOT realization, addressability, surgery geometry and capacity, decoder/reaction, factory/buffer service, cycles, runtime, physical qubits, and failure.

## 2026-09-07 — OOP/IP branch-maximum PPM-weight comparison

**Status:** Reviewed and approved (`T-20260907-002`, `RV-20260907-005`, 2026-09-07)

What changed:

- Evaluated the reviewed OOP 15/30 and IP 30/60 schedules with the same
  deterministic 512-branch protocol, recording the largest PPM support weight
  in every candidate level and branch.
- Separated p50/p95/p99, the maximum over 510 hashed assignments, two forced
  all-zero/all-one boundary branches, and the reviewed support ceiling.
- Replayed all 46,080 level--branch values with a separate scalar
  implementation, covering 11,326,464 branch--PPM evaluations in total.
- Added a compressed OOP/IP switch view showing the demand schedule and the
  complete branch-weight summary curves.

Why it matters:

The scalar headline 509 hides the shape of the workload: it is driven by the
forced all-one boundary branch in both variants. OOP/IP p95 peaks are 168/188,
p99 peaks are 198/222, and hashed-assignment maxima are 223/248, while the
separate OOP exact/IP may-support ceilings are 1,003/1,006. The IP reverse half
adds sustained distributional load, but this sample does not turn the large
ceiling gap into a probability or native-cost claim. Native time, geometry,
routing, factory, decoder, space, and failure remain null. The reviewer
independently reimplemented the support-propagation rule a third time with a
set-based data structure, computed both deterministic forced boundary
branches from scratch (catching and fixing a bug in that script), and
matched the full sampled maximum of 509 to the exact claimed level for both
variants; separately recomputed every quantile and hotspot directly from the
stored vectors for all 90 levels and matched the contract's table exactly.
See `docs/WIDTH256_OOP_IP_BRANCH_WEIGHT_SAMPLING_CONTRACT.md` and
`coordination/reviews/T-20260907-002.md`. This closes the width-256 OOP/IP
structural comparison cycle; no task is yet claimed for the next
native-mapping step.

## 2026-09-07 — Width-256 in-place commutation-aware QCLA rerun

**Status:** Reviewed and approved (`T-20260907-001`, `RV-20260907-004`, 2026-09-07)

What changed:

- Extended the approved CCX relation to the in-place modulo-`2^256` source,
  retaining both X and CNOT layers as global source-Clifford barriers.
- Scanned all 3,019,653 ordered CCX pairs and matched the complete oracle to a
  linear-size rank/parent certificate and a thirty-event critical path.
- Reduced the structural result from source-aligned 34 macros / 68 candidates
  to 30 / 60 while retaining all 1,229 CCXs in the coherent reverse cleanup.
- Exhaustively replayed the independently reordered schedules for all 87,376
  input pairs at widths 2--8, preserving in-place addition and clean ancillas.
- Recomputed all 14,748 PPM profiles with 512 deterministic branches plus a
  sound may-support envelope. Maximum sampled/upper PPM weight is 509/1,006,
  witnessed/may contact is 633/634, and level-union upper bound is 1,770.

Why it matters:

The native mapper can now be tested against both a clean OOP 15/30 control and
the harder IP 30/60 workload, which exposes reverse cleanup, X barriers, 495
source ancillas, and stronger branch-dependent contact. The 30/60 depth is
`PROVED` only inside the stated logical dependency model; support remains
`CHECK`, and all native time, geometry, routing, factory, decoder, physical-
qubit, and failure outputs are null. The reviewer independently reimplemented
the complete pairwise-dependency and longest-path computation from scratch
against the real IP source trace, matching every headline pair-oracle number
and the full macro-layer size vector exactly, and independently confirmed by
hand calculation that X on a CCX control does not commute with that CCX,
justifying the X-barrier extension. See
`docs/WIDTH256_IP_COMMUTATION_AWARE_QCLA_CONTRACT.md` and
`coordination/reviews/T-20260907-001.md`. This closes the joint-CCX/
commutation-aware validation cycle for both OOP and IP width-256 workloads;
no task is yet claimed for the next native-mapping step.

## 2026-09-07 — Width-256 commutation-aware QCLA rerun

**Status:** Reviewed and approved (`T-20260906-004`, `RV-20260907-003`, 2026-09-07)

What changed:

- Replaced the quadratic saved pair table with one compact rank record per
  CCX, then independently rescanned all 754,606 pairs to check it.
- Reduced the exact logical unitary result from the source-aligned 17 macros /
  34 two-phase candidates to 15 / 30, with a matching fifteen-event critical
  path.
- Recomputed support at each common macro entry for all 7,374 PPMs. The peak
  logical burst is 255 CCZ states; possible PPM weight, level union, and
  contact maxima are 1,003, 1,647, and 54.
- Tested all 240 width-256 measurement cleanups and rejected them under the
  present Z/X-only family: a retained conditional CZ turns cleanup `X(p)`
  into branch-dependent mixed `X(p)Z(q)`. No cleanup CCX was removed.

Why it matters:

The commutation argument now gives a smaller exact width-256 logical
critical path, but the cleanup shortcut does not scale for free. The selected
result remains the unitary 15/30 candidate. Support unions are not
simultaneous branch weights or native geometry, and cycles, runtime, physical
qubits, failure, routing, reactions, and factory service remain null/open.
The reviewer independently reimplemented the complete pairwise-dependency
and longest-path computation from scratch against the real width-256 source
trace, matching all five headline pair-oracle numbers and the full
macro-layer size vector exactly; algebraically re-derived the cleanup
mixed-axis identity; and independently confirmed the required structure
holds for all 240 (not sampled) cleanup candidates. See
`docs/WIDTH256_COMMUTATION_AWARE_QCLA_CONTRACT.md` and
`coordination/reviews/T-20260906-004.md`. No task is yet claimed for a
native mapper/finite backend over these certified logical results.

## 2026-09-07 — Exact small-width commutation-aware QCLA schedules

**Status:** Reviewed and approved (`T-20260906-003`, `RV-20260907-002`, 2026-09-07)

What changed:

- Built a separate dependency model for every clean OOP-QCLA width from 2 to
  8. It keeps noncommuting CCX order and source CNOT barriers, and removes only
  serialization admitted by the reviewed common-frame joint-injection rule.
- Proved the resulting macro-depth exactly inside that complete logical model
  by matching each earliest-rank construction to a critical-path lower bound.
- Kept source/unitary/measured results side by side. At width 5 they are
  6/4/3 macro-layers, or 12/8/6 two-phase direct-CCZ candidate levels.
- Verified measurement cleanup across every input and outcome branch. It
  shortens depths at widths 5 and 7 but not 6 or 8, where another critical
  path remains.

Why it matters:

The former width-5 8/6 envelopes are now reviewed exact schedules in the stated
architecture-independent logical model. They are still
not surgery rounds or time: reaction frontiers retain every predecessor
outcome conservatively, their duration is unknown, and physical support,
routing, decoding, factory service, space, and failure remain absent. Width
256 is unchanged at 34 reviewed source-aligned candidate levels until the next
gated task. Independent replay checked 776 pair decisions, 39,824 truth-table
rows, 174,752 arithmetic runs, 337,920 measured branches, and 337,908 relative
phase pairs with zero mismatch. The full suite has 370 passes and the same two
unrelated sibling-pin failures. The reviewer independently reimplemented the
whole pairwise-dependency-plus-longest-path scheduler from scratch, matched
the exact macro-depth table at every width, re-derived all five aggregate
totals from first principles, verified the optimality argument
mathematically, and hand-traced both width-8 measurement-uncompute cleanups.
See `docs/COMMUTATION_AWARE_QCLA_SCHEDULING_CONTRACT.md` and
`coordination/reviews/T-20260906-003.md`. The next executable task is
unassigned `T-20260906-004`.

## 2026-09-07 — Width-5 joint direct-CCZ semantic gate

**Status:** Reviewed and approved (`T-20260906-002`, `RV-20260907-001`, 2026-09-07)

What changed:

- Proved inside the positive-control CCX model that two CCXs commute exactly
  when neither target is used as a control by the other. The exact width-5
  source has 45 pairs: 36 commute and nine do not.
- Replayed the four proposed unitary macro-groups (sizes 4/3/2/1) under one
  common incoming frame. Ten fresh resource triples, canonical corrections,
  all 64 single-event branches, both actual shared-control anchors, and one
  synthetic shared-target anchor pass without an event-to-event reaction edge.
- Replaced the final cleanup CCX in a separate candidate by destructive
  `X(p:1:1)` plus conditional `CZ(b:2,b:3)`. All 1,024 width-5 input columns
  and 2,048 outcome branches pass, including 2,046 relative-phase checks.
  The resulting frame remains live through four later CNOTs and reaches a
  conservative six-value final support; it is not counted as free cleanup.

Why it matters:

This admits the four unitary and three measured-cleanup macro-groups as
semantic inputs to the next small-width dependency task. It does **not** yet
prove that the corresponding 8/6 two-phase levels are schedules, optimal, or
physically executable. The reviewed 12-level width-5 and 34-level width-256
baselines remain unchanged, and native cycles, time, physical qubits, and
failure probability remain null. Fourteen focused and 64 related tests pass;
the full suite has 352 passes and the same two unrelated sibling-pin failures.
The reviewer independently reimplemented the commutation classifier and a
differently-structured joint-injection statevector simulator from scratch,
matching the claimed 36/9 pair split and probability/operator error
magnitudes exactly, and hand-derived the measurement-uncompute phase identity
and frame-propagation support. See `docs/JOINT_DIRECT_CCZ_WIDTH5_CONTRACT.md`
and `coordination/reviews/T-20260906-002.md`.

## 2026-09-06 — Joint-CCX validation and width-256 re-evaluation plan

**Status:** Reviewed and approved (`T-20260906-001`, `RV-20260906-001`, 2026-09-06)

What changed:

- Recorded a validation-first plan asking whether the reviewed direct-CCZ QCLA
  dependency model is over-serialized by conservative nearest-use wire edges.
- Proposed two width-5 alternatives to the reviewed 10-CCX/12-level baseline:
  a four-macro-layer/eight-level unitary grouping, and a three-macro-layer/
  six-level grouping that replaces the final uncompute with a destructive
  measurement plus conditional-frame update.
- Gated any adoption behind three sequential proofs: exact width-5 logical
  commutation and joint-injection verification, a commutation-aware
  small-width (2-8) dependency model, and only then a width-256 structural
  rerun.

Why it matters:

Both proposed reductions remain `CONJECTURE` until their own task closes; the
existing 12-level width-5 and 34-level width-256 source-aligned results are
explicit, unchanged baselines. The reviewer independently reconstructed the
ten-gate width-5 CCX list and every claimed gate-overlap relationship directly
from the reviewed circuit builder and found no transcription error. See
`docs/JOINT_CCX_QCLA_REEVALUATION_CYCLE.md` and
`coordination/reviews/T-20260906-001.md`. The planned semantic gate is now
implemented and reviewed in `T-20260906-002` (`RV-20260907-001` `APPROVED`).

## 2026-09-05 — H/CNOT logical policy and QEC execution options

**Status:** Reviewed and approved (`T-20260905-001`, `RV-20260905-001`, 2026-09-06). The H option is now explicitly self-derived `NUMERICAL`, and the Xu et al. Figure 11(c) citation remains only on measurement CNOT. A repository-owned exact channel verifier checks all four H-teleportation outcome branches: each has probability `1/4` within `5.551115123125783e-17`, and the corrected branch operator matches H with maximum Frobenius residual `1.1102230246251565e-16`. Replay rejects an incorrect evidence label or renewed Xu attribution. Claude independently re-derived the same channel with a second, differently-coded script and matched every number exactly before approving. See `coordination/reviews/T-20260905-001.md`.

What changed:

- Compared frame-conjugated logical, bare logical, and frame-tracked handling
  separately for H and CNOT under one exact correction-frame convention.
- Proved that all three CNOT choices preserve Z-only data PPMs, although
  support and routing can grow; only frame-conjugated H preserves that
  guarantee in general, and bare/tracked H has an explicit Y witness.
- Extracted width-256 OOP/IP demand: 34/68 H layers, 3/4 CNOT-only layers,
  and maximum same-layer H/CNOT counts 255/256.
- Compared whole-event co-design, global H-SWAP and transversal CNOT, one-bit
  H and measurement-CNOT teleportation, and addressable deformation/surgery.
- Kept RASCqL timing arithmetic in its own source domain and left every
  current-backend finite output null.

Why it matters:

This separates two questions that were previously mixed together: which
logical frame policy keeps high-rate PPMs Z/X-only, and which code mechanism
can actually execute that policy. The proposed default is frame-conjugated H
plus bare CNOT. A native H-SWAP or H-teleport gadget implements bare H, so it
still needs frame clearing, an H-safe proof, or whole-event co-design.

Starting from 34/68 direct-CCZ candidate levels, one-layer-H plus SIMD-CNOT
gives conditional-overlap totals 54/106 or strict totals 71/140. H teleport
plus measurement CNOT gives 94/182 or 111/216. These are logical primitive
layers, not QEC cycles. See
`docs/HIGH_RATE_QCLA_H_CNOT_STRATEGY_CONTRACT.md` and
`coordination/reviews/T-20260905-001.md`.

## 2026-09-03 — Scalable direct-CCZ PPM support hypergraphs

**Status:** Reviewed and approved (`T-20260903-002`, `RV-20260903-002`)

What changed:

- Proved the exact support-update rule for source CNOTs and the two target-
  touching conditional corrections, then matched every component ANF at OOP/IP
  widths 5 and 8.
- Falsified the initial outcome-independent-support hypothesis with a minimal
  exact width-5 witness: one later PPM contains `a:0` iff one earlier outcome
  bit is one.
- Generated exact OOP possible-support unions for 19 widths through 257. At
  width 256, the largest union is 1,003 and the largest batch contact is 129.
- For IP-256, separated the 512-branch witnessed-union/contact lower bounds
  935/523, actual sampled single-branch maximum weight 509, and sound may-
  support/contact upper bounds 1,006/567. The unsaturated gap stays `CHECK`.
- Added compiler/scheduler-free independent reconstruction at widths 5, 8,
  and 256, full width-256 hypergraphs, mutation tests, and null finite outputs.

Why it matters:

The previous compatibility proof establishes that a logical batch is
same-axis and commuting, but it does not make its support fixed. A native
mapper must now handle branch-dependent support or specify which frame terms
are materialized. A possible-support union may combine different branches; it
is not a simultaneous physical support, surgery depth, or runtime.

Evidence: `FALSIFIED` outcome independence; `PROVED` OOP exact unions and
support-update rule; `NUMERICAL` exact-anchor equivalence; `CHECK` large-IP
union gap; `OPEN` native execution. See
`docs/DIRECT_CCZ_QCLA_SCALABLE_SUPPORT_CONTRACT.md` and
`coordination/reviews/T-20260903-002.md`.

> [!success] Review note
> The support-update algebra (sparse Boolean-ANF propagation of `C†Z(q)C`
> through source CNOTs and the two support-changing conditional corrections)
> is genuinely new math for this line. Rather than trust a manual tableau
> derivation -- which produced suspicious results on paper -- Claude's review
> independently cross-checked the certificate's exact support activities
> against the already matrix-verified full symbolic compiler's
> presented-observable computation, using hand-written comparison code, across
> all 522 PPMs at widths 5 and 8 for both variants. Zero mismatches. It also
> independently reproduced the outcome-independence falsification witness by
> direct inspection, confirmed the large-IP may-support envelope is sound by
> construction (every update is a monotonic set union, never a removal) by
> reading the code, and verified every width-256 bound ordering the model
> requires. See `coordination/reviews/T-20260903-002.md`.

## 2026-09-03 — Scalable direct-CCZ PPM compatibility

**Status:** Reviewed and approved (`T-20260903-001`, `RV-20260903-001`)

What changed:

- Replaced the unverified source two-phase envelope with a linear-size proof
  certificate. Conditional `X/Z/CNOT/CZ` frames preserve Z-type observables,
  so phase-1 `ZZ` measurements stay same-axis and Y-free; fresh-resource
  phase-2 `X` measurements are disjoint and absent from the frame.
- Checked source-layer support disjointness, strictly later dependencies,
  exact source/event DAG preservation, one event per Toffoli, canonical six-
  PPM event shape, and resource uniqueness for 19 OOP/IP widths through 257.
- At width 256, certified 34 OOP and 68 IP unitless candidate levels. Both
  constructions meet their causal lower bounds while avoiding the
  27,184,251/108,744,378 possible global pair records.
- Matched the full-ANF OOP/IP width-5/8 schedules by batch hash and validated
  all 2,466 materialized within-batch relations and Y-free profiles.
- Added an independent source-only replay plus deterministic first-witness
  rejection for malformed axes/frames and fail-closed finite-output tests.

Why it matters:

Width-256 logical compatibility is no longer an extrapolation from small
instances: it follows from a generator-closure argument whose premises are
checked in linear trace size. However, the result remains inside the logical
candidate screen. It provides no physical simultaneous-measurement gadget,
routing, duration, capacity, decoder, factory/buffer, qubit, or failure model.
The 34/68 values are not surgery rounds or runtime.

Evidence: `PROVED` generator closure and model-relative optimal candidate
counts; `NUMERICAL` exact-anchor bridge; `OPEN` finite execution. See
`docs/DIRECT_CCZ_QCLA_SCALABLE_COMPATIBILITY_CONTRACT.md` and
`coordination/reviews/T-20260903-001.md`.

> [!success] Review note
> This was the mathematically deepest submission in the direct-CCZ line, so
> Claude's review went beyond structural checking into independent
> mathematical verification of the theorem itself. It wrote a from-scratch
> numpy script -- no import of the reviewed code -- that built explicit
> unitary matrices for X, Z, CNOT, and CZ and exhaustively confirmed
> (148 cases on 2- and 3-qubit systems) that conjugation by any of them
> preserves the Z-type Pauli subspace, that H is exactly the primitive that
> breaks this, and that any two Z-type Paulis automatically commute with no
> possible Y content. A second from-scratch script, importing only the
> already-reviewed source-trace and event builders, independently re-derived
> every structural premise the theorem depends on (fresh disjoint resources,
> canonical six-PPM shape, CZ/Z/X-only corrections confined to event data,
> disjoint source-layer support, layer-advancing dependencies, X/CNOT-only
> passthroughs) at widths 5, 8, 17, and 256 for both variants -- 56 checks,
> zero failures. It also hand-verified the OOP width-5 within-batch pair
> count (186) against the generated data and confirmed via `git diff --stat`
> that the task touches no previously reviewed compiler, architecture, or
> batching code. See `coordination/reviews/T-20260903-001.md`.

## 2026-09-03 — Direct-CCZ QCLA width scaling

**Status:** Reviewed and approved (`T-20260901-010`, `RV-20260901-009`)

What changed:

- Added exact full-pair anchors at widths 5 and 8. OOP/IP candidates use
  12/24 levels at width 5 and 14/28 at width 8, each meeting its exact causal
  lower bound without fallback.
- Added a compact source/event traversal for 19 widths through 257. It records
  exact gates, events, PPMs, cleanup, layer bursts, and a weighted source-DAG
  causal lower bound without building every PPM pair.
- Directly evaluated width 256: OOP/IP has 1,229/2,458 CCZ events,
  7,374/14,748 PPMs, and causal lower bounds 34/68. Both peak at 255 events or
  1,530 PPMs in one source layer.
- Added an independent replay with no compiler or scheduler imports and
  mutation tests for pair counts, exact levels, and forbidden finite runtime.
- Preserved the rejected finite backend and left native schedule, surgery
  rounds, memory/routing, controller/factory service, runtime, physical
  qubits, and failure probability null.

Why it matters:

The width-256 workload is now measured directly without attempting to store
27,184,251 OOP or 108,744,378 IP pair records. Small-width exact equality with
the causal bound remains an anchor, not an extrapolated large-width schedule.
Across the selected widths, IP event count, non-Clifford source-layer count,
and causal lower bound are twice OOP; this is `NUMERICAL`, not a theorem.

Evidence: `NUMERICAL` structural results, model-relative `PROVED` exact
width-5/8 anchors and causal lower-bound construction, `CHECK` two-phase
source envelope, and `OPEN` width-256 compatibility/finite service. See
`docs/DIRECT_CCZ_QCLA_SCALING_CONTRACT.md` and
`coordination/reviews/T-20260901-010.md`.

> [!success] Review note
> Claude's review confirmed via `git diff --stat` that this task adds one new
> module and only additive exports, leaving every already-reviewed compiler,
> architecture, and batching module untouched. It independently re-derived
> that the weighted-causal-lower-bound rule (weight two per Toffoli, zero per
> Clifford) is a valid general lower bound from the already-verified
> two-layer Figure-14(a) event structure, not an empirical fit at the two
> anchor widths, and confirmed the analyzer actively cross-validates this
> bound against the full exact symbolic causal path at widths 5 and 8. A
> from-scratch verification script importing only the already-reviewed
> source-trace builders -- never the reviewed scaling module, compiler, or
> scheduler -- independently reproduced every headline number at seven widths
> spanning 5 through 256 (including 1,229/2,458 events, 7,374/14,748 PPMs,
> 27,184,251/108,744,378 theoretical pairs, and causal bounds 34/68 at width
> 256) using its own independently implemented longest-path algorithm, and
> separately confirmed the power-of-two boundary pattern matches standard
> parallel-prefix carry-lookahead theory. See
> `coordination/reviews/T-20260901-010.md`.

## 2026-09-02 — IP-QCLA direct-CCZ comparison

**Status:** Reviewed and approved (`T-20260901-009`, `RV-20260901-008`)

What changed:

- Reused the reviewed direct-CCZ PPM/conditional-frame representation for the
  in-place width-5 QCLA without passing through the seven-T CCX decomposition.
- Represented all 20 Toffolis as 120 PPMs and retained all source X/CNOT frame
  effects, 75 dependencies, and logical/resource lifetimes explicitly.
- Added independent serialized semantic and batching replay, including all
  1,024 basis inputs and all 7,140 PPM-pair certificates.
- Constructed 24 unitless candidate levels matching a 24-level causal lower
  bound. Seven large-frame profiles visibly use conservative weight bounds;
  pair compatibility remains exact.
- Generated a deterministic OOP/IP report and retained the rejected finite
  backend with null schedule, runtime, physical-qubit, and failure outputs.

Why it matters:

The clean OOP and in-place variants can now be compared under the same logical
direct-CCZ semantics. At width 5 the source/event/candidate-level counts double
from OOP to IP, while peak semantic liveness remains 26. This is a bounded
logical result, not evidence for doubled wall-clock runtime or an executable
backend.

Evidence: `NUMERICAL`, with model-relative `PROVED` 24-level optimality and a
`CHECK` boundary on seven profile-weight summaries. See
`docs/DIRECT_CCZ_IP_QCLA_COMPARISON_CONTRACT.md` and
`coordination/reviews/T-20260901-009.md`.

> [!success] Review note
> Claude's review was the first in this line to touch the core compiler and
> scheduler rather than a presentation layer. It proved by code-structure
> reading that the already-reviewed OOP path degenerates byte-for-byte to its
> pre-existing behavior, independently re-derived that the new exact-ANF
> axis-existence test used for profiles above 16 variables is mathematically
> identical to the brute-force enumeration it replaces, and confirmed the
> `minimum_weight=1`/support-union `maximum_weight` bounds are valid (a
> Clifford conjugate of a nonidentity Pauli is never the identity). A
> from-scratch verification script importing none of the reviewed modules ran
> a 120,000-point Monte Carlo cross-check (400 sampled pairs x 300 random
> assignments) against every claimed commutation/axis-conflict/Y decision with
> zero contradictions, independently reimplemented the causal longest-path
> algorithm from raw JSON and reproduced the 24-level bound exactly, and
> hand-verified all combinatorics (7,140 pairs, 336 within-batch, 6,804
> cross-level). See `coordination/reviews/T-20260901-009.md`.

## 2026-09-02 — Direct-CCZ PPM audit atlas

**Status:** Reviewed and approved (`T-20260901-008`, `RV-20260901-007`)

What changed:

- Generated one overview and one static SVG panel for each of the nine source
  macro-layers directly from the reviewed symbolic trace and batching data.
- Kept PPM-free CNOT layers visible and displayed frame-in/out, source gates,
  PPM/outcome records, outcome-to-frame updates, candidate colors and labels,
  separation certificates, and separate general/finite status.
- Added an independent verifier that imports neither the renderer, compiler,
  nor scheduler, reconstructs the projection from serialized inputs, and parses
  every SVG as XML.

What we learned:

- The ten panels cover all 23 source operations, 60 PPMs/outcomes, 60 frame
  updates, and 36 source dependencies exactly once.
- Of 1,770 PPM pairs, 186 lie within candidate batches and 1,584 cross levels.
  The atlas retains every cross-level certificate and labels compatible pairs
  separated only by the global construction as `deterministic_frontier_partition`.
- Manual raster inspection caught palette, portable-glyph, and bottom-clipping
  defects that the semantic checks alone did not expose; targeted regressions
  now cover each issue.

> [!warning] Interpretation
> This atlas is a `NUMERICAL` audit projection of reviewed evidence. Every SVG
> says `candidate_batch_level_not_time`. Color equality does not establish
> physical simultaneity, and the atlas adds no native schedule, runtime,
> physical-qubit count, or failure probability.

> [!success] Review note
> Claude's review independently reconstructed every displayed count from raw
> Phase-A/Phase-B JSON with scripts that import neither the atlas builder, the
> renderer, nor the repository's own replay module -- including a regex-based
> SVG scan as a genuinely different parse method from the reviewed module's
> XML-based one -- and matched all counts exactly (60 PPM-to-batch
> memberships, 186 within-batch pairs, 1,584 cross-level certificates with the
> full reason tally, and complete 23/60/60/36 source/PPM/update/dependency
> coverage). It specifically isolated the 378
> `deterministic_frontier_partition`-only pairs and confirmed from the raw
> relation table that every one is genuinely conflict-free, substantiating the
> "not a physical conflict" claim from data rather than trusting the doc. It
> regenerated the 14-artifact experiment twice with independently-computed
> byte-identical hashes, and rasterized and visually inspected four
> structurally distinct panels (overview, densest, PPM-free, multi-batch),
> finding no clipping or legibility defects. See
> `coordination/reviews/T-20260901-008.md`.

Canonical record: [[docs/DIRECT_CCZ_PPM_ATLAS_CONTRACT|PPM audit-atlas contract]] · [[context/RESULT_LEDGER#R-20260901-007|Atlas result]]

## 2026-09-01 — Direct-CCZ PPM candidate batching

**Status:** Reviewed and approved (`T-20260901-007`, `RV-20260901-006`)

What changed:

- Classified all 1,770 pairs of the 60 symbolic PPMs using exact Boolean
  commutation and per-logical-index axis formulas.
- Built two deterministic 12-level candidate schedules, while separately
  emitting a rejected finite-backend verdict and a 60-operation low-rate
  semantic order.
- Added an independent serialized replay that reconstructs every relation,
  causal/reaction path, liveness count, lower bound, and output class.

What we learned:

- No width-5 PPM has branch-possible Y content; 30 pairs have a nonzero
  commutator and 30 have a local axis conflict.
- Six compatible pairs share logical support, confirming that support overlap
  alone must not force serialization.
- The optimized candidate uses batches of 12, 12, 6, 6, then eight groups of
  3. Its 12 levels meet both a causal and a conflict-clique lower bound of 12.
- Peak demand in the stated logical-liveness coordinate is 26 logical values
  and four live CCZ resource states; maximum presented PPM weight is seven.

> [!warning] Interpretation
> The 12 levels are unitless logical candidates, not surgery rounds or time.
> The selected finite backend remains rejected with its schedule, runtime,
> physical-qubit total, and failure probability all null. Product rewrites and
> selective frame materialization have zero admitted transforms, and the
> singleton fallback's finite cost is `OPEN`.

> [!success] Review note
> Claude's review independently reimplemented the entire DAG-closure and
> pairwise-relation model from scratch, matching every claimed count exactly
> after catching and fixing a bug in its own first attempt (comparing PPMs'
> raw nominal logical support instead of their frame-corrected presented
> support, which had produced 0 instead of the claimed 6 compatible
> overlapping pairs). It then independently re-validated the actual 12-level
> schedule end to end with zero compatibility or causality violations found,
> and independently re-derived the peak liveness figures from the contract's
> stated rule. See `coordination/reviews/T-20260901-007.md`.

Canonical record: [[docs/DIRECT_CCZ_PPM_BATCHING_CONTRACT|PPM batching contract]] · [[context/RESULT_LEDGER#R-20260901-005|Candidate result]] · [[context/RESULT_LEDGER#R-20260901-006|Finite/fallback gap]]

## 2026-09-01 — Symbolic direct-CCZ PPM/frame trace

**Status:** Reviewed and approved (`T-20260901-006`, `RV-20260901-005`)

What changed:

- Lowered the reviewed width-5 clean OOP-QCLA directly through the exact
  six-PPM direct-CCZ event, without the seven-T decomposition.
- Kept measurement outcomes as exact Boolean expressions in a canonical
  conditional-Clifford frame and recorded the observable presented to every
  later PPM.
- Preserved operation/source dependencies and logical/resource lifetimes, then
  added a separate serialized replay that rebuilds them from scratch.

What we learned:

- The 23 source gates produce ten injections, 60 PPMs, 60 conditional frame
  updates, thirteen pass-through CNOTs, and zero compiler ancillas.
- Independent replay checks 640 local correction rows, 23 frame transitions,
  3,840 presented-observable cases, all 1,024 basis inputs, and the 64-branch
  local injection channel.
- Exact symbolic outcomes avoid enumerating the global `2^60` tree; the 64
  global probes are regression coverage, not exhaustive verification.

> [!warning] Interpretation
> This is a semantic compiler trace, not a physical schedule. The nine source
> layers are not surgery rounds, pass-through CNOT costs remain `OPEN`, and no
> high-rate batch, runtime, physical-qubit total, or failure result was emitted.

> [!success] Review note
> Claude's review independently verified every primitive Clifford-conjugation
> rule against explicit unitary matrices and reconstructed a nontrivial later
> PPM's presented observable end to end -- catching a bug in its own first
> reconstruction attempt (a missed passthrough-CNOT frame-reconjugation replay
> step) before confirming an exact match with the compiler's stored output.
> See `coordination/reviews/T-20260901-006.md`.

Canonical record: [[docs/DIRECT_CCZ_PPM_TRACE_CONTRACT|Symbolic PPM/frame contract]] · [[context/RESULT_LEDGER#R-20260901-003|Trace result]] · [[context/RESULT_LEDGER#R-20260901-004|Schedule gap]]

## 2026-09-01 — AutoCCZ surface-code adapter qualification

**Status:** Reviewed and approved (`T-20260901-001`, `RV-20260901-001`)

What changed:

- Pinned the Gidney--Fowler AutoCCZ and base-factory PDFs plus four official
  layout/calculator assets.
- Added a 17-field gate that distinguishes a real source-native adapter from a
  complete decoded and buffered service.
- Independently checked the abstract consumer on all 64 measurement branches
  and recomputed the paper example's factory arithmetic.

What we learned:

- The surface-code factory, three delayed-choice CZ fixups, six routing qubits,
  and one Toffoli consumer form one source-native adapter.
- Under `CHECK` inputs, the factory bottleneck is 135 cycles/CCZ or about
  7.407 kHz, requiring fourteen factories for 100 kHz average demand.
- Complete service is not closed: nine fields are missing, and the official
  `5.33332e-11` error uses `d1=15,d2=31` rather than the selected
  `d1=17,d2=27` model.

> [!warning] Interpretation
> Adapter admission is not service admission. The branch check is an abstract
> logical-consumer check, not a surface-code noise simulation. No width-256
> schedule, runtime, machine-size total, or failure result was emitted.

> [!success] Review note
> Claude's review rendered Figures 3, 4, and 6 of the primary AutoCCZ PDF
> directly at 300 DPI and confirmed the delayed-choice-cell abstraction and
> routing/consumer-port structure are faithfully transcribed, and separately
> unzipped and parsed the official ODS calculator's raw XML to confirm its
> `5.33332e-11` output-error cell is in the same column as `d1=15` and that
> `d1=17` never appears in the sheet -- independently settling the
> calculator-incompatibility claim from the spreadsheet itself. See
> `coordination/reviews/T-20260901-001.md`.

Canonical record: [[docs/AUTOCCZ_SURFACE_CODE_ADAPTER|AutoCCZ adapter]] · [[context/RESULT_LEDGER#R-20260901-001|Channel result]] · [[context/RESULT_LEDGER#R-20260901-002|Service gap]]

## 2026-08-31 — Finite direct-CCZ backend compatibility audit

**Status:** Reviewed and approved (`T-20260831-004`, `RV-20260831-004`)

What changed:

- Audited seven pinned primary PDFs, including finite tricycle CCZ generation,
  batched high-rate qLDPC operations, finite T ports, and in-situ Y injection.
- Added a 17-field gate that keeps source-reported values, admitted values,
  evidence labels, and architecture compatibility domains separate.
- Added boundary tests for forged admission, missing fields, a complete
  coherent backend, and a complete but mixed-domain backend.

What we learned:

- The selected Cain ECC-256 `P=20` candidate has 13 missing finite fields.
- Cain's available batch-10, 120-cycle, approximately-`1e-10` factory values
  are qualified but belong to the incompatible `bb18` space/balanced regime.
- The exact Figure 14(a) event is portable, but no finite decoded
  factory-to-consumer adapter closes the physical backend.

> [!warning] Interpretation
> This is an `OPEN` negative admission result, not proof that a finite
> direct-CCZ backend is impossible. It says that the pinned corpus does not
> close this candidate without cross-architecture substitution. No schedule,
> runtime, physical-qubit total, or failure estimate was emitted.

> [!success] Review note
> Claude's review pulled the raw Cain PDF text at the pages reporting the
> `bb18` factory figures and at the time-efficient appendix, and found the
> source itself distinguishes the two architecture regimes in its own prose
> -- directly confirming the audit's compatibility-domain claim rather than
> merely re-checking the implementer's own labeling. See
> `coordination/reviews/T-20260831-004.md`.

Canonical record: [[docs/DIRECT_CCZ_FINITE_BACKEND_AUDIT|Finite backend audit]] · [[context/RESULT_LEDGER#R-20260831-006|Result R-20260831-006]]

## 2026-08-31 — Exact single-event direct-CCZ channel

**Status:** Reviewed and approved (`T-20260831-003`, `RV-20260831-003`)

What changed:

- Read the full-resolution correction labels in Litinski--Nickerson Figure
  14(a) and pinned the measurement-bit convention plus all six conditional
  correction expressions.
- Added an independent six-qubit projector reconstruction that imports neither
  the capability loader nor the event compiler.
- Split isolated-event admission from finite high-rate service and preserved
  the complete source dependency graph in direct-CCZ event-trace schema v2.

What we learned:

- All 64 measurement branches are nonzero, have probability `1/64`, and match
  ideal CCX with zero operator Frobenius residual at floating-point precision.
- Width 256 emits 1,229 typed injection events, 7,374 PPM/outcome records,
  3,955 source dependencies, and 766 pass-through CNOTs.
- The exact event channel is now admitted, but high-rate timing, logical error,
  decoder/reaction capacity, ports, routing, factory delivery, buffering, and
  storage remain `OPEN`.

> [!warning] Interpretation
> This is a `NUMERICAL` single-event semantic result, cross-reviewed and
> approved. It is not a finite schedule, physical-qubit estimate, failure
> result, or runtime.

> [!success] Review note
> Claude's review additionally rendered the primary source PDF page to a 600
> DPI image and directly pixel-verified every wire assignment and correction
> formula in Figure 14(a) against the machine-encoded map, and independently
> wrote a from-scratch numpy channel reconstruction (before reading the
> repository's own verifier) that reproduced all 64 measurement branches at
> matching precision. See `coordination/reviews/T-20260831-003.md`.

Canonical record: [[docs/DIRECT_CCZ_SINGLE_EVENT_CONTRACT|Single-event contract]] · [[context/RESULT_LEDGER#R-20260831-004|Channel/event result]] · [[context/RESULT_LEDGER#R-20260831-005|High-rate gap]]

## 2026-08-31 — Clean OOP-QCLA and direct-CCZ capability gate

**Status:** Reviewed and approved (`T-20260831-002`, `RV-20260831-002`)

What changed:

- Generated a deterministic clean out-of-place modulo-`2^n` QCLA trace and
  replayed every computational-basis input through width 6.
- Audited the pinned direct-CCZ, high-rate injection, and factory sources into
  one machine-readable capability record.
- Added a typed direct-CCZ adapter that refuses to emit events until the exact
  correction map is source-qualified; high-rate scheduling has a separate,
  stricter field gate.

What we learned:

- Width 256 has 1,229 Toffolis, 766 CNOTs, 20 source layers, 240 clean prefix
  scratch values, and 1,008 fully resident source values.
- A single-injection six-PPM skeleton is literature-supported, but the exact
  outcome-to-CZ/Pauli map is still `OPEN` in the executable schema.
- Cain's ten-CCZ/120-cycle factory observation does not close delivery,
  buffering, routing, decoder, reaction, ports, or storage. The current
  high-rate schedule is therefore correctly absent.

> [!warning] Interpretation
> The generated source-layer CCZ-candidate demand is `NUMERICAL`; the native
> capability conclusion is `OPEN`. No QEC-cycle, wall-clock, physical-qubit,
> or success-probability result was produced.

Canonical record: [[docs/DIRECT_CCZ_CAPABILITY_AND_OOP_QCLA_CONTRACT|Capability/OOP-QCLA contract]] · [[context/RESULT_LEDGER#R-20260831-002|OOP result]] · [[context/RESULT_LEDGER#R-20260831-003|Capability gap]]

## 2026-08-31 — Direct-CCZ high-rate QCLA research plan

**Status:** Reviewed and approved (`T-20260831-001`, `RV-20260831-001`)

Human-directed planning record, not an implementation. It selects clean out-of-place modulo-\(2^{256}\) QCLA as the first workload for studying direct \(|CCZ\rangle\) injection (as opposed to the already-reviewed seven-\(T\) route), and requires a pinned native injection/reaction/factory/routing/failure contract before any runtime is reported.

What we learned:

- At \(n=256\), the isolated carry-status prefix network needs 974 CCXs; the clean out-of-place adder needs 1,229 (974 plus 255 initial-generate gates); the already-reviewed in-place adder needs 2,458. All three numbers were independently re-derived from the Draper formulas during review and matched exactly.
- Direct CCZ injection capability and parallel high-rate batching beyond the demonstrated ten-XX case remain `OPEN` -- no runtime, physical-qubit, or success-probability claim is made.

Canonical record: [[docs/HIGH_RATE_QCLA_DIRECT_CCZ_RESEARCH_CYCLE|Direct-CCZ research cycle]] · [[context/DECISIONS#D-0014|Decision D-0014]]

## 2026-08-26 — Width-256 QCLA memory and high-rate schedule

**Status:** Reviewed and approved (`T-20260825-002`, `RV-20260825-002`)

What changed:

- Split QCLA clean workspace into reviewed reuse epochs while keeping `A/B`
  inputs and outputs as strict memory values.
- Added deterministic farthest-next-use placement and an independent replay
  that rejects free copies, use before origin, invalid returns, or occupancy
  above the 60-slot J300 budget.
- Compared one-scratch serial, ten-scratch serial, and ten-scratch high-rate
  schedules and emitted the complete shifted width-256 T-demand timeline.

What we learned:

- One-scratch serial uses 46,355 loads/stores; ten-scratch serial uses 53,514,
  exposing the traffic cost of shrinking source payload from 59 to 50 slots.
- Ten-scratch high-rate selects 1,576 exact-ten-XX batches. Its provisional
  schedule is 2,420,527 rounds, 169,260 (6.54%) below one-scratch serial even
  though it performs 7,433 more reloads.
- All three policies conserve total T-state demand 17,206, but the emitted
  timeline assumes ideal supply and contains no factory service or stalls.

> [!warning] Interpretation
> Placement/action invariants are exact under the contract, while the generated
> counts are `NUMERICAL` and the transfer/native/clean-lifecycle timing is
> `CHECK`. This fixed order is neither optimal nor a lower bound, and it excludes
> routing, decoding, failure, factory buffering, and wall-clock conversion.

Canonical record: [[context/RESULT_LEDGER#R-20260825-002|Placement result]] · [[context/RESULT_LEDGER#R-20260825-003|Timing sensitivity]] · [[docs/QCLA_MEMORY_IO_CONTRACT|QCLA memory-I/O contract]]

## 2026-08-25 — QCLA adaptive-PBC and resident high-rate boundary

**Status:** Reviewed and approved (`T-20260825-001`, `RV-20260825-001`)

What changed:

- Pinned Selinger circuit (1) as an exact, ancilla-free seven-T-family CCX and
  independently reconstructed its complete three-qubit channel.
- Preserved every QCLA gate's layer, prefix stage, direction, and exact CCX
  column while re-deriving dependencies from expanded wire use.
- Reused the reviewed adaptive-PBC compiler and J300 scheduler, adding only a
  deterministic X-frame expression and a fail-closed resident-capacity gate.

What we learned:

- The CCX reconstruction agrees with ideal Toffoli to
  `2.220446049250313e-16` maximum absolute error (`NUMERICAL`).
- Width 14 fits with ten scratch slots (58/60) and exposes nine ten-XX batches;
  its `CHECK` schedule changes from 94,161 to 93,108 provisional rounds.
- Width 256 expands to 40,857 primitives and 17,206 T-state demands, but needs
  1,008 resident slots with one scratch and is rejected before scheduling.

> [!warning] Interpretation
> The seven-T path is a comparison baseline, not a claim over direct CCZ.
> Width-256 memory traffic is handled by the following cycle; routing, factory
> service, decoding, failure, and wall-clock time remain open.

Canonical record: [[context/RESULT_LEDGER#R-20260825-001|Result R-20260825-001]] · [[docs/QCLA_PBC_LOWERING_CONTRACT|QCLA PBC contract]]

## 2026-08-24 — Source-pinned carry-lookahead DAG

**Status:** Reviewed and approved (`T-20260824-003`, `RV-20260824-003`)

What changed:

- Audited the exact in-place, modulo-`2^n`, no-carry-in variant directly from
  Draper et al. and reconstructed its ten reversible steps.
- Preserved the `P/G/C/P^-1` prefix rounds and their bounded-fan-out overlaps,
  while deriving DAG edges from actual wire use rather than source-list order.
- Added explicit carry/prefix-ancilla lifetimes, including two scratch-reuse
  epochs, and an independent X/CNOT/Toffoli basis replay.
- Generated a fail-closed, deterministic width-256 structure and layerwise
  Toffoli-demand artifact.

What we learned:

- All 5,456 basis-input pairs across widths 2--6 pass with `A` preserved,
  `B=A+B mod 2^n`, and every ancilla cleaned.
- Width 256 uses 2,458 Toffolis, 1,019 CNOTs, 510 NOTs, and 495 source
  ancillas. Its source schedule and dependency critical path are both 40.
- Peak demand is 255 Toffolis in one source layer, making burst service and
  processor capacity central questions for the next lowering cycle.

> [!warning] Interpretation
> The 40 layers are not QEC cycles, and 495 logical circuit ancillas are not a
> physical-qubit total. No high-rate-surgery legality, memory traffic, factory
> supply, routing, decoding, or failure budget is included yet.

Canonical record: [[context/RESULT_LEDGER#R-20260824-004|Result R-20260824-004]] · [[docs/QCLA_DAG_CONTRACT|QCLA DAG contract]]

## 2026-08-24 — Bell-bridge teleportation ripple adder

**Status:** Reviewed and approved (`T-20260824-001`, `RV-20260824-001`)

What changed:

- Pinned Xu et al. Figure 6 and the Active Volume bridge/adder figures by PDF
  hash, then represented the carry links as acyclic prepare, use, Bell-measure,
  rebind, and reaction events.
- Kept Bell carry carriers separate from memory load/store ownership and added
  an independent lifecycle replay that rejects premature use or rebind.
- Added exhaustive width-2--4 classical-basis addition checks and a branchwise
  arbitrary-state check for the generic Bell bridge.
- Added a normalized lane sweep with optional exact-ten-disjoint-`XX` batches,
  strict rejection of unresolved timing, and time-stamped resource-state
  demand.

What we learned:

- Width 32 changes from 64 to 37 normalized steps on one Bell-measurement lane
  when three ten-`XX` batches are admitted.
- With two or more Bell-measurement lanes, both policies take 34 steps, so the
  reaction/dependency chain becomes the bottleneck in this model.
- The width-256 structural trace has 255 bridges, 1,532 events, and a peak of
  765 provisional bridge carriers; this is not a physical-qubit count.

> [!warning] Interpretation
> The complete Xu Figure-6 phase channel has not been independently
> reconstructed. All finite times are `CHECK` normalized steps, not HGP/J300
> cycles or wall-clock time, and ideal supply does not model factory stalls.

Canonical record: [[context/RESULT_LEDGER#R-20260824-001|Result R-20260824-001]] · [[context/RESULT_LEDGER#R-20260824-002|Result R-20260824-002]] · [[docs/TELEPORTATION_BRIDGE_RIPPLE_CONTRACT|Bell-bridge contract]]

## 2026-08-23 — Memory–processor I/O overlay

**Status:** Reviewed and approved (`T-20260823-001`, `RV-20260823-001`)

What changed:

- Ported the reviewed `runtime-metadata-benchmark` memory-I/O semantics (value origin, fixed-order Belady retention, maximal-prefix partitioning, and independent replay) as a source-pinned overlay on the existing Gidney DAG, without changing the DAG schema itself.
- Connected the overlay to the reviewed adaptive-PBC event order: memory transfers are scheduled around a fixed compute order rather than jointly optimized with it.
- Added an independent replay engine that recomputes every load/store decision from scratch and rejects duplicate loads, stores of non-resident values, or any leftover processor occupancy at the end.

What we learned:

- All admitted legacy width-2--4 exact partition reference cells reproduce exactly (e.g. width 2 needs 4 loads/4 stores at generous capacity, or 6/6 at tighter capacity).
- Under a one-lane, one-round-per-transfer sensitivity profile with no prefetch, the reviewed width-32 J300 schedule grows from 31,176 to 31,376 rounds, using 100 loads and 100 stores.
- Zero-duration transfers preserve every reviewed compute event's start and end exactly, confirming the overlay does not silently change the already-approved schedule when I/O is idealized away.

> [!warning] Interpretation
> Memory-transfer duration and the fixed-order/no-prefetch policy are `CHECK` sensitivity choices, not literature-backed executable architecture. The 100-load/100-store width-32 figure is a policy/order observation, not a placement lower bound.

Canonical record: [[context/RESULT_LEDGER#R-20260823-001|Result R-20260823-001]] · [[context/RESULT_LEDGER#R-20260823-002|Result R-20260823-002]] · [[docs/MEMORY_IO_EXECUTION_CONTRACT|Memory I/O contract]]

## 2026-08-15 — J300 adaptive-PBC scheduling

**Status:** Reviewed and approved (`T-20260815-005`, `RV-20260815-007`)

What changed:

- Connected the reviewed adaptive Pauli trace to explicit J300 operation-zone, scratch-slot, carrier, and classical-reaction resources.
- Separated source-supported operation size from source-supported operation time.
- Made strict mode reject every unresolved time or space entry instead of silently using a placeholder.
- Tested the exact-ten-disjoint-XX high-rate rule with one and ten compiler scratch slots.

What we learned:

- Gidney widths 2, 4, 16, and 32 expose zero eligible ten-XX batches under the current trace and greedy resource rules.
- A synthetic ten-independent-CNOT trace does produce one batch, changing the sensitivity schedule from 550 to 433 rounds (`NUMERICAL`).
- The width-32 sensitivity schedule is 31,176 syndrome rounds, but unresolved J300 timings make this `CHECK`, not an executable runtime.
- The 2,074 physical-qubit figure is only the known J300-plus-full-extractor component peak; it excludes several unresolved components.

Canonical record: [[context/RESULT_LEDGER#R-20260815-004|Result R-20260815-004]] · [[docs/J300_PBC_SCHEDULING_CONTRACT|J300 scheduling contract]]

## 2026-08-15 — Adaptive PBC/CQLU lowering

**Status:** Reviewed and approved (`T-20260815-004`, `RV-20260815-006`)

What changed:

- Replaced placeholder CNOT/H/S/T names with explicit state preparations, Pauli measurements, classical dependencies, and Pauli-frame updates.
- Kept arithmetic outputs quantum rather than applying a final-classical-output PBC theorem outside its contract.
- Checked every nonzero branch of the CNOT, H, S, T, and T-dagger gadgets on fixed and seeded small states.

What we learned:

- The maximum channel-check error was below `1e-15` (`NUMERICAL`).
- The compiler needs one reusable scratch logical slot in a serialized operation zone.
- Width 58 fits the J300 60-slot count exactly; width 59 now requires 61 slots.
- Strict runtime is still blocked by state preparation, Z/ZZ/ZX durations, reaction time, conditional CZ, and adaptive scheduling.

Canonical record: [[context/RESULT_LEDGER#R-20260815-003|Result R-20260815-003]] · [[docs/PBC_CQLU_LOWERING_CONTRACT|PBC/CQLU contract]]

## 2026-08-15 — Obsidian Research Hub

**Status:** Reviewed and approved (`T-20260815-003`, `RV-20260815-005`)

- Added a plugin-free visual entry point for the project.
- Separated reviewed work, work under review, human decisions, and provisional `CHECK` results.
- Linked the human-readable views directly to the canonical task, evidence, review, and technical records.

## 2026-08-15 — First Mitten scheduling cycle

**Status:** Reviewed and approved (`T-20260815-002`, `RV-20260815-004`)

What changed:

- Expanded the Gidney temporary logical AND into a phase-exact Clifford+T trace.
- Encoded a finite-size Mitten processor configuration with parameters `n=300`, `k=60`, and `d=14`.
- Added deterministic greedy scheduling and an explicit strict/provisional boundary.
- Limited high-rate surgery to the directly supported batch of ten disjoint XX measurements.

What we learned:

- The direct Gidney erase operations are single-X measurements, so the current high-rate ten-XX rule has no hits.
- Width 59 fills all 60 source-residency slots; width 60 is rejected at source occupancy 61.
- The eventual executable boundary may be lower because the future PBC compiler can require additional logical ancillas.

> [!warning] Interpretation
> The 15,270-round width-59 result is a `CHECK` sensitivity result under placeholder operation times, not a verified physical runtime.

Canonical record: [[context/RESULT_LEDGER#R-20260815-002|Result R-20260815-002]] · [[docs/MITTEN_GIDNEY_LOWERING_CONTRACT|Lowering contract]]

## 2026-08-15 — QEC-neutral Gidney DAG

**Status:** Reviewed and approved (`T-20260815-001`, `RV-20260815-003`)

What changed:

- Connected the pinned, independently verified Gidney implementation through a versioned read-only interface.
- Generated a causal DAG without baking in a QEC architecture.
- Represented X-basis erasure measurement and conditional Clifford correction as separate nodes connected by a classical dependency.
- Checked exact small-width fixtures and the width-256 circuit structure.

Why it matters:

The scheduler can now distinguish mathematical circuit parallelism from parallelism that an actual code and processor can execute.

Canonical record: [[context/RESULT_LEDGER#R-20260815-001|Result R-20260815-001]] · [[docs/GIDNEY_DAG_CONTRACT|DAG contract]]

## 2026-08-11 to 2026-08-15 — Literature and baseline preparation

**Status:** Reviewed and approved (`T-20260811-001`, `T-20260811-002`)

- Indexed 14 verified primary-source PDFs with local metadata and reading notes.
- Compared candidate ECDLP-256 circuits and recorded mismatched count conventions and unresolved semantic checks.
- Recommended Schrottenloher 2026 as the first source baseline and Luo et al. v2 as a dynamic-circuit contrast, pending the human-owned final selection.

Canonical record: [[docs/CANONICAL_CIRCUIT_DECISION|Circuit decision support]] · [[literature/papers/INDEX|Paper index]]
