# AI handoff

Last updated: 2026-09-07
From: claude
To: codex and human

## Current review handoff

`T-20260906-003` is `RV-20260907-002` `APPROVED` (Claude review, 2026-09-07).
It implements the separate commutation-aware clean OOP-QCLA dependency model
at widths 2--8 after the approved width-5 semantic gate.

Every ordered CCX pair is independently truth-table classified. The DAG keeps
source order for noncommuting target--control overlap and for any pair crossing
a source CNOT layer; other pairs may share one approved common-frame macro.
Earliest longest-path ranks form legal layers and meet an explicit critical-
path lower bound, proving exact macro-depth within this complete logical model.
Source/unitary/measured depth is `1/1/1, 2/2/2, 3/3/3, 6/4/3, 6/4/4,
7/5/4, 7/5/5`. With two direct-CCZ candidate levels per macro, width 5 is
therefore source 12, unitary 8, and measured cleanup 6.

The measured variant removes `0/0/0/1/1/2/2` certified final cleanup CCXs.
Independent complete arithmetic and phase replay shows that cleanup reduces
depth at widths 5 and 7 but not at 6 or 8, where another critical path remains.
The verifier imports neither the new scheduler nor the joint direct-CCZ
compiler and checks 776 pair decisions, 39,824 pair truth-table rows, 174,752
arithmetic runs, 337,920 measured branch columns, and 337,908 relative-phase
pairs with zero mismatch.

The result deliberately retains all six outcome tokens per predecessor CCX at
each inter-macro reaction boundary. This frontier is conservative `CHECK`;
the minimal outcome subset and reaction duration remain unresolved. The exact
claim is therefore logical macro-depth only, not native cycles or time. Width
256 has not been rerun and remains at its reviewed source-aligned 34 candidate
levels. Placement, routing, ports, memory, decoding/reaction, factory/buffer,
physical qubits, failure, and every finite output remain null.

Eighteen focused and 55 related tests pass. The full suite has 370 passes and
only the same two unrelated sibling source-pin failures. Ruff and strict mypy
pass; compileall, Hub validation, and final deterministic regeneration are
recorded in `coordination/sessions/T-20260906-003.md`.

The reviewer independently reimplemented the entire pairwise-dependency and
ASAP-longest-path scheduler from scratch (not importing the reviewed
scheduler or its shipped replay module), running it against the real,
already-reviewed `build_oop_qcla_trace` for every width 2--8 and both
variants, and reproduced the exact `1/1/1, 2/2/2, 3/3/3, 6/4/3, 6/4/4, 7/5/4,
7/5/5` macro-depth table exactly. It independently re-derived all five
aggregate replay totals from first principles (776 pairs via
`sum(C(n,2))`; 39,824 truth-table rows via `sum(2^|union support|)`; 174,752
arithmetic inputs via `sum(4^width)*2`; 337,920 branch columns and 337,908
relative pairs via the branch/relative-pair formulas applied to widths 5--8)
and matched every one exactly. It verified the ASAP-layering optimality claim
mathematically: a dependency edge always strictly increases longest-path
depth, and this propagates correctly through transitive chains even without
an explicit transitive edge, so the "PROVED optimal within this stated
logical model" claim is not merely an empirical observation. It hand-traced
both width-8 measurement-uncompute cleanups from the raw gate list (producer,
last quantum use, frame propagation) and found the generated
`cleanup_records` matched exactly, including two disjoint final frame
supports. It also located and spot-checked the out-of-repository public
width-5 "Parallelization audit" page (a local file on this machine, not a
remote claim) and found its `CHECK`/"not physical time" labeling and its
"Width 256 is not revised yet" disclaimer consistent with the reviewed
claims, though it could not independently verify the page's full rendering.
See `docs/COMMUTATION_AWARE_QCLA_SCHEDULING_CONTRACT.md`, experiment
`E-20260906-003`, and `coordination/reviews/T-20260906-003.md`.

Approval of `RV-20260907-002` clears the dependency gate for the still-unassigned
`T-20260906-004` width-256 structural rerun.

## Previous approved handoff

`T-20260906-002` is `RV-20260907-001` `APPROVED` (Claude review, 2026-09-07).
It closes the bounded logical-semantic gate required before building a
separate commutation-aware dependency trace; it does not yet admit that
trace, an exact schedule, or a width-256 rerun.

The exact positive-control CCX truth-table classifier proves that two CCXs
commute iff neither target is a control of the other. It checks all 45 pairs
among the ten pinned width-5 source CCXs (36 commuting, nine noncommuting;
2,040 basis rows) plus synthetic representatives of every overlap class. The
four proposed unitary macro-groups have sizes 4/3/2/1 and pass common-frame
primitive factorization with ten fresh resource triples, all 64 single-event
branches, both actual shared-control anchors, one synthetic shared-target
anchor, canonical corrections, and no event-to-event reaction edge. The
largest joint probability/operator residual is
`5.692061405548898e-19`/`2.4854698590557027e-18`.

The measured-cleanup alternative replaces final operation
`qcla-oop:000012` by destructive `X(p:1:1)` plus outcome-conditioned
`CZ(b:2,b:3)`. Independent full-width replay passes all 1,024 input columns,
2,048 outcome branches, and 2,046 relative-phase comparisons with zero output
or dirty-ancilla mismatch. The outcome-dependent frame is not discarded: it
propagates through four later CNOTs and conservatively reaches
`{a:2,a:3,b:2,b:3,z:2,z:3}`; the width-5 suffix contains no later PPM.

The semantic result admits the four unitary and three measured-cleanup
macro-groups as inputs to `T-20260906-003`. Their 8/6 two-phase values remain
`CHECK` envelopes, not schedules, lower bounds, optimality results, surgery
rounds, or time. The reviewed width-5 12-level and width-256 34-level baselines
remain unchanged, and native cycles, seconds, physical qubits, and failure
remain null. Assumption identifiers were normalized at task entry: H
teleportation retains `A-0045`, joint direct CCZ is `A-0046`, and measurement
uncompute is `A-0047`. Fourteen focused and 64 related tests pass; the full
suite has 352 passes plus the same two unrelated sibling-pin failures. See
`docs/JOINT_DIRECT_CCZ_WIDTH5_CONTRACT.md`, experiment `E-20260906-002`, and
`coordination/reviews/T-20260906-002.md`.

The reviewer independently re-derived every headline number from scratch
without importing the new compiler or its shipped replay module: a
from-scratch commutation classifier reproduced the exact 36/9 pair split and
overlap-kind breakdown; a differently-structured tensor-based statevector
simulator (explicit `numpy` reshaping/`tensordot`, not the reviewed code's
bit-shift indexing) reproduced the joint-injection channel for both real
shared-control anchors and matched the probability/operator error magnitudes
to the same digit; the measurement-uncompute phase-cancellation identity was
re-derived algebraically (`p:1:1` already equals `b:2 AND b:3` at the
replaced gate, so the destructive-`X` and conditional-`CZ` phases are
identical and cancel to a constant `1/sqrt(2)`); and the four-gate
frame-propagation and final support `{a:2,a:3,b:2,b:3,z:2,z:3}` were
confirmed by hand-tracing the raw gate list. Regenerated artifacts twice from
a clean directory, byte-identical both times and matching the independent
derivations. Reran the full suite (352 passed, same two known unrelated
failures). The reviewer also flagged that the assumption-ID collision this
task fixes (`A-0045` reused by both the H-teleportation and joint-CCX
assumptions) was present when `RV-20260906-001` was approved and was missed
in that review; it is recorded as a bookkeeping oversight, not a scientific
defect, and this task's fix and transparent disclosure in
`docs/JOINT_CCX_QCLA_REEVALUATION_CYCLE.md` are correct.

`T-20260905-001` is `RV-20260905-001` `APPROVED` (Claude re-review,
2026-09-06), closing the sole defect from the first-pass review. The
`one_bit_h_teleportation` option is now a self-derived `NUMERICAL` identity;
it no longer cites Xu et al. The Xu Figure 11(c) `LITERATURE` citation remains
only on measurement CNOT. A new independent operator-channel verifier checks
all four `ZX`/destructive-`X` outcome branches for the `|0>` carrier, obtains
probability `1/4` per branch within `5.551115123125783e-17`, and matches H up
to the branch Pauli correction with maximum Frobenius residual
`1.1102230246251565e-16`; the reviewer independently re-derived this exact
channel with a second, differently-coded script and matched every number
including the scalar corrections (`0.5, 0.5, 0.5, -0.5`). Replay rejects
renewed Xu attribution or an H evidence label other than `NUMERICAL`, and the
reviewer confirmed the corresponding mutation test actually exercises this
guard. `A-0042` now records only the cited measurement-CNOT assumption and
`A-0045` records the H identity. Six focused tests, 11 combined strategy/Hub
tests, Ruff, strict mypy, compileall, generation, replay, and mutation checks
pass; the full suite has 338 passes and only the same two unrelated
sibling-pin failures -- all independently reproduced by the reviewer, including
two independent byte-identical artifact regenerations matching the
implementer's recorded hashes exactly. The layer counts, logical envelopes,
frame-conjugated-H plus bare-CNOT policy, and null native outputs are
unchanged from the first pass.

Review history: `T-20260905-001` received `RV-20260905-001`
`CHANGES_REQUESTED` (Claude review,
2026-09-06). The task separates the logical H/CNOT frame policy from the
code-side realization question, and the review confirmed every part of that
separation except one citation.

Under `physical = C^dagger logical`, the independently replayed six-row matrix
finds that only frame-conjugated H generally preserves the existing Z-only
direct-CCZ phase-1 invariant. Bare or tracked H has an explicit two-qubit
mixed-axis/Y witness. All three CNOT modes preserve Z type by closure of the
`X/Z/CNOT/CZ` subgroup, but bare/tracked CNOT can grow, reroute, and retain
branch dependence in later support. Fresh-resource phase-2 readouts remain
X-only in every case. The proposed logical default is therefore
frame-conjugated H plus bare CNOT, pending review.

Width-256 OOP/IP has 17/34 Toffoli-bearing layers and 3/4 CNOT-only layers,
giving 34/68 H layers with maximum parallel demand 255 and CNOT-layer maximum
256. Starting from the reviewed 34/68 candidate levels, one-layer-H plus SIMD
CNOT gives conditional overlap totals 54/106 or strict totals 71/140.
One-bit-H teleportation plus measurement CNOT gives 94/182 or 111/216. These
are logical primitive-layer envelopes only. The overlap version assumes the
closing H/H-teleport step can overlap the disjoint fresh-resource-X phase.

The H teleportation gadget needs one provisioned `|0>` carrier per parallel H
and ordered `ZX`, `X` measurements; the CNOT gadget needs one `|+>` scratch
per parallel CNOT and ordered `ZZ`, `XX`, `Z` measurements. Neither consumes
T/CCZ magic states. H-SWAP and H teleportation implement bare H, not the
selected frame-conjugated H, unless the frame is cleared, the target is
proved H-safe, or the whole conjugated-H/direct-CCZ event is co-designed.

RASCqL Table 1/2 values are retained only as an incompatible-domain `CHECK`
comparator. They yield OOP 65.1/73.6 ms and IP 124.2/141.2 ms for the
overlap/strict H-SWAP+tCNOT arithmetic while excluding relabel debt. They are
not current direct-CCZ runtime. Current-backend cycles, seconds, physical
qubits, and failure remain null.

Five focused tests pass; the full suite has 337 passes and only the two known
unrelated sibling-pin failures. Ruff, strict mypy, compileall, deterministic
generation, independent replay, and mutation checks pass. See
`docs/HIGH_RATE_QCLA_H_CNOT_STRATEGY_CONTRACT.md`,
`experiments/runs/T-20260905-001/summary.json`, and
`coordination/reviews/T-20260905-001.md`.

The review independently reconstructed the H/Y witness and the CNOT-closure
argument from explicit numpy matrices, independently re-extracted every
width-256 OOP/IP layer count directly from the reviewed QCLA builders (not the
new module) and matched them exactly, independently recomputed every
strict/overlap added-layer total and the RASCqL-domain millisecond totals from
the stated formulas, and directly pixel-verified the RASCqL Table 1/2 values
and the CNOT-teleportation gadget against Xu et al. Figure 11(c) with zero
discrepancies. It reproduced the 5 focused tests, ran ruff/strict
mypy/compileall clean on all new files, and regenerated the six-artifact
experiment twice with independently confirmed byte-identical hashes.

The review found one defect: the `one_bit_h_teleportation` execution option's
citation to "Xu et al. 2024, arXiv:2407.18490v1, Figure 11" is wrong. Page 28
of that source shows only (a) generic `ZZ`+destructive-`X` teleportation on a
`|+>` ancilla, (b) a teleported S gate, and (c) measurement-based CNOT (the
gadget correctly cited elsewhere in the same record); it contains no
one-bit-H-teleportation panel, and the paper's actual Hadamard method
(Section 5) is an unrelated global fold-transversal H-SWAP technique. An
independent from-scratch numpy simulation (20 random states, exact
statevector arithmetic) confirms the `ZX`-then-`X`, `|0>`-ancilla gadget
described in the contract is nonetheless mathematically correct -- it reaches
fidelity 1.0 to `H|psi>` on every outcome branch via one deterministic Pauli
correction -- so this is a citation/evidence-label defect (the claim should be
`NUMERICAL`/re-sourced rather than `LITERATURE`/Xu-Figure-11), not a
computational error, and it does not affect any other finding, the width-256
layer-demand numbers, or the null current-backend outputs. See
`coordination/reviews/T-20260905-001.md` for the complete finding list and
required changes.

That requested change has now been implemented in
`src/ecdlp_ftqc/analysis/qcla_clifford_strategy.py`, the contract, and the
assumption ledger: the accurate CNOT half retains its
`LITERATURE`/Xu-Figure-11(c) label, while the H half is recorded separately as
the self-derived `NUMERICAL` assumption `A-0045`. The re-review independently
verified the fix rather than trusting the implementer's report: it re-read the
updated `ExecutionOption` record and the new
`verify_one_bit_h_teleportation_channel`/`_h_teleportation_branch_operator`
functions, ran them directly, then wrote a second independently-coded script
using a different derivation (explicit basis-vector projectors and a
separately-derived probability formula) that reproduced the identical branch
operators, scalars, and error magnitudes to the last bit; confirmed the
mutation-rejection test genuinely reinstates an Xu citation and checks replay
raises on it; reran the focused and full test suites, ruff, and strict mypy;
and regenerated the experiment twice, matching both the implementer's recorded
hashes and each other byte-for-byte. `T-20260905-001` is now `DONE` and its
lock is `RELEASED`. See `coordination/reviews/T-20260905-001.md` for the
complete re-review.

`T-20260903-002` is `RV-20260903-002` `APPROVED` (Claude review, 2026-09-03).
It adds logical-support hypergraphs for the reviewed source-aligned direct-CCZ
candidate levels and separates exact possible-support unions, sampled lower
witnesses, and sound may-support upper envelopes.

The initial hypothesis is `FALSIFIED`: Z-type closure does not make support
outcome-independent. The first exact OOP width-5 witness is
`direct-ccz:000005:ppm:zz_0`, where logical value `a:0` has activity ANF
`direct-ccz:000000:outcome:zz_1`. Its zero/one assignments remove/add that
component. Exact OOP/IP widths 5 and 8 match every component ANF and the first
witness in the reviewed full symbolic trace.

All 19 selected OOP widths through 257 use exact Boolean-ANF possible-support
propagation. At OOP width 256, 7,374 PPMs contain 1,924 branch-dependent
profiles; the largest exact possible-support union is 1,003 and the largest
within-batch possible-contact count is 129. A possible-support union may
combine values occurring in different branches and is not a simultaneous
branch weight.

IP widths above 8 use a sound may-support upper envelope plus 512 deterministic
concrete branches. At width 256, 14,748 PPMs contain 5,355 observed branch-
dependent profiles. The witnessed possible-support-union lower bound is 935,
the maximum support weight actually present in one sampled branch is 509, and
the witnessed contact lower bound is 523. The may-support upper bounds are
1,006 and 567. Because 4,462 profiles retain 118,501 unwitnessed may-
incidences, large-IP exact support remains `CHECK`, not `PROVED`.

The independent replay imports neither compiler nor scheduler, checks source
identity/counts for all 38 certificates, and reconstructs the full logical
support claims at widths 5, 8, and 256, including both 256-bit hypergraphs.
Noncanonical correction maps and hypergraph mutation fail closed. All native
schedule, surgery-round, runtime, placement/routing, processor/factory,
physical-qubit, and failure outputs remain null. See
`docs/DIRECT_CCZ_QCLA_SCALABLE_SUPPORT_CONTRACT.md`,
`experiments/runs/T-20260903-002/summary.json`, and
`coordination/reviews/T-20260903-002.md`.

Rather than hand-derive the two-sided CNOT-conjugation tableau algebra (an
error-prone manual exercise that produced suspicious intermediate results on
paper), the reviewer independently cross-checked the certificate's exact
support activities against the already matrix-verified full symbolic
compiler's `presented_observable` z/x-components using hand-written
comparison code -- not the reviewed comparison function -- across all 522
PPMs at widths 5 and 8 for both variants, finding zero mismatches and
correctly identifying every branch-dependent component. The reviewer
independently reproduced the outcome-independence falsification witness by
direct inspection, matching the claim exactly; confirmed the large-IP
may-support envelope is sound by construction (every update is a monotonic
set union, never a removal) by reading the code rather than only observing
it empirically; and verified all width-256 bound orderings (witnessed-union
<= may-support upper bound, single-sampled-branch weight <= witnessed union,
witnessed contact <= upper contact) hold from the generated summary.
`git diff --stat` confirmed the task touches no previously reviewed
compiler, architecture, batching, or compatibility-certificate code.

No task currently holds an active lock; `T-20260903-002`'s lock is
`RELEASED`. The next open item is implementing one coherent native mapper or
explicit frame-materialization policy for the branch-dependent width-256
support hypergraphs (no task ID claimed yet), alongside the separate
factory/buffer/routing and AutoCCZ finite-field work already tracked below.

`T-20260903-001` is `RV-20260903-001` `APPROVED` (Claude review, 2026-09-03).
It replaces the large-width `CHECK` two-phase envelope with a linear-size
logical compatibility certificate. Under the reviewed frame normal form,
conditional `X/Z/CNOT/CZ` generators preserve branchwise Z-type Paulis. Each
source layer's phase-1 resource-data `ZZ` PPMs are therefore same-axis,
commuting, and Y-free; phase-2 resource `X` readouts are disjoint on globally
fresh resource values absent from the frame. The certifier also checks exact
source/event DAG preservation, support-disjoint source layers, strictly
layer-advancing dependencies, one event per Toffoli, canonical six-PPM event
shape, and resource uniqueness.

All 19 selected OOP/IP widths through 257 pass without materializing a global
pair table. Width-256 OOP/IP now has 34/68 unitless logical candidate levels
for 1,229/2,458 events and 7,374/14,748 PPMs; both constructions meet the
weighted causal lower bound. The 27,184,251/108,744,378 possible global pairs
remain unmaterialized. The largest candidate batch is 765 PPMs; 1,530 is the
combined demand of both ordered phases in one source layer.

Full-ANF OOP/IP widths 5/8 match every compact batch-membership digest and
validate all 2,466 materialized within-batch pairs, Y-free profiles, candidate
counts, and causal bounds. Independent replay imports neither compiler nor
scheduler and rebuilds all 38 certificates. Hash and finite-runtime tampering
fail; malformed axes and non-CSS frame generators return the first
`FALSIFIED` witness and no candidate count. Twenty-five focused and 61 combined
tests pass; the full suite reports 323 passes plus the two known unrelated
sibling-pin failures. Ruff, strict mypy on 54 source files plus the generator,
compileall, and two genuine consecutive byte-identical regenerations of all
six outputs pass.

The result is `PROVED` only inside the architecture-independent logical
screen. It does not supply a code-level simultaneous PPM construction, native
surgery rounds, physical support/placement, routing, source-Clifford or basis-
change duration, reaction/decoder service, factory/buffer service, physical
qubits, or failure probability. All finite outputs remain null. See
`docs/DIRECT_CCZ_QCLA_SCALABLE_COMPATIBILITY_CONTRACT.md`,
`experiments/runs/T-20260903-001/summary.json`, and
`coordination/reviews/T-20260903-001.md`.

The reviewer independently proved the generator-closure theorem itself from
scratch with an explicit numpy matrix construction (X/Z/CNOT/CZ conjugation
preserves the Z-type Pauli subspace across 148 exhaustive test cases on 2- and
3-qubit systems; H breaks it exactly as claimed; any two Z-type Paulis
provably commute; Y-content is automatically impossible) rather than trusting
the docstring, then independently re-derived that the actual OOP/IP source and
event traces satisfy every premise the theorem depends on -- fresh disjoint
resources, the canonical six-PPM shape, CZ/Z/X-only deferred corrections
confined to event data, disjoint source-layer support, strictly
layer-advancing dependencies, and X/CNOT-only passthroughs -- at widths 5, 8,
17, and 256 using a script that imports neither the certifier nor the
compiler. Hand-verified the OOP width-5 within-batch pair count (186) against
the generated summary, and confirmed via `git diff --stat` that this task
touches no previously reviewed compiler, architecture, or batching code.

`T-20260903-002` holds a `REVIEW` lock while Claude reviews the support
certificate. After approval, the next evidence-producing action is to define
one coherent native mapping policy for branch-dependent logical support, or
to prove which frame terms must be materialized before mapping. No subsequent
task is claimed yet.

`T-20260901-010` is `RV-20260901-009` `APPROVED` (Claude review, 2026-09-03).
It adds exact Boolean-ANF anchors at widths 5 and 8, then switches to a compact
source/event traversal for 19 OOP/IP widths through 257 without materializing
quadratic PPM pair tables. The four exact OOP/IP anchors use 12/24 levels at
width 5 and 14/28 at width 8; every construction meets its exact causal lower
bound and contains no fallback PPM.

The direct width-256 structural result has 1,229/2,458 OOP/IP direct-CCZ
events, 7,374/14,748 PPMs, theoretical pair tables of
27,184,251/108,744,378 records, and weighted causal lower bounds 34/68. Both
variants peak at 255 events or 1,530 PPMs in one source layer. Across the 19
selected widths, IP event count, non-Clifford source-layer count, and causal
lower bound are exactly twice OOP; this is labeled `NUMERICAL` for the selected
sweep, not a general proof.

The independent replay imports neither compiler nor scheduler, rebuilds all
38 structural points, and detects mutations to a pair count, exact level, and
prohibited finite runtime. The source two-phase envelope is only `CHECK` and
is not a large-width schedule. Width-256 compatibility remains `OPEN`.
The selected finite gate still has 13 capability gaps, 13 backend gaps, three
incompatible factory fields, and four missing native-mapper obligations, so
all native schedule/time/space/failure outputs remain null. Ten focused tests
pass; the full suite reports 298 passes plus the two known unrelated
sibling-pin failures. See `docs/DIRECT_CCZ_QCLA_SCALING_CONTRACT.md`,
`experiments/runs/T-20260901-010/summary.json`, and
`coordination/reviews/T-20260901-010.md`.

The reviewer confirmed via `git diff --stat` that this task adds one new
module plus purely additive exports and leaves every already-reviewed
compiler/architecture/batching module untouched, independently re-derived
that the weighted-causal-bound rule is a valid general lower bound from the
already-verified two-layer Figure-14(a) event structure (not an empirical fit
at the two anchor widths), and confirmed the analyzer actively cross-validates
this bound against the full exact symbolic causal path at widths 5/8 rather
than only asserting it. A from-scratch verification script importing only the
already-reviewed source-trace builders (never the reviewed scaling module,
compiler, or scheduler) independently reproduced every headline number at
seven widths spanning 5 through 256 using its own independently implemented
longest-path algorithm, including the width-256 figures and the exact
IP-equals-2x-OOP relation at every tested width, and separately confirmed the
power-of-two boundary pattern matches standard parallel-prefix
carry-lookahead theory.

## Reviewed IP-QCLA direct-CCZ foundation

`T-20260901-009` is `RV-20260901-008` `APPROVED` (Claude review, 2026-09-02).
The width-five in-place modulo-QCLA now uses the same
architecture-independent six-PPM direct-CCZ and ordered conditional-Clifford-
frame IR as the reviewed clean OOP trace, without the Selinger seven-T route.
Its 43 source operations map to 20 events, 120 PPMs, 120 conditional updates,
15 pass-through CNOTs, and eight pass-through X gates over 18 source layers,
with all 75 dependencies preserved and no compiler ancilla.

Independent serialized replay imports neither compiler nor scheduler and
checks 1,280 local correction rows, all 43 source frame transitions, 14,880
presented-observable probes, all 1,024 width-five basis inputs, and the local
64-branch injection channel with zero operator residual. Independent batching
replay rebuilds all 120 profiles and 7,140 pair certificates. Exact ANF
compatibility gives a deterministic 24-level construction matching the exact
causal lower bound 24. Seven late-frame profiles exceed exact branch-weight
enumeration: their pair compatibility remains exact, while weight is visibly
reported only as proved lower/upper bounds and distinct-observable count is
null under `A-0037`.

The OOP/IP comparison records 10/20 direct-CCZ events, 12/24 unitless
candidate levels, 36/96 reaction boundaries, and 5/17 explicitly scoped
cleanup operations. Neither count is physical time. Finite execution remains
rejected with 13 capability gaps, 13 backend gaps, three incompatible factory
fields, four native-mapper obligations, and null native schedule/runtime/
physical-qubit/failure outputs. Widths 2--5 pass exhaustive independent source
replay; twelve focused cases, 178 combined related cases, and 288 full-suite
cases pass, with only the two known unrelated sibling-pin failures remaining.
Ruff, strict mypy on 49 library files plus the generator, and byte-identical
two-run regeneration of all 11 artifacts pass. Reviewer findings are in
`coordination/reviews/T-20260901-009.md`; the contract is
`docs/DIRECT_CCZ_IP_QCLA_COMPARISON_CONTRACT.md`.

The reviewer proved by code-structure reading (not just by test) that the OOP
path degenerates byte-for-byte to its pre-existing behavior, independently
re-derived that the new exact-ANF axis-existence test used for profiles above
16 variables is mathematically identical to the brute-force enumeration it
replaces, confirmed the `minimum_weight=1`/support-union `maximum_weight`
bounds are valid proved/conservative bounds (a Clifford conjugate of a
nonidentity Pauli is never the identity), and confirmed the 120-vertex
large-instance conflict-clique shortcut can never corrupt the PROVED-
optimality claim since the causal bound alone already closes it. A from-
scratch verification script that imports none of the reviewed modules ran a
120,000-point Monte Carlo cross-check (400 sampled pairs x 300 random
assignments) against every claimed commutation/axis-conflict/Y decision with
zero contradictions, independently reimplemented the causal DAG longest-path
algorithm from raw JSON and reproduced the 24-level bound exactly, and
hand-verified all combinatorics (7,140 pairs, 336 within-batch, 6,804
cross-level).

`T-20260901-010` consumed these reviewed dependencies and is now
`RV-20260901-009` `APPROVED`.

## Reviewed high-rate-aware QCLA-to-PPM foundation

`T-20260901-008` is `RV-20260901-007` `APPROVED` (Claude review, 2026-09-02).
The deterministic audit atlas regenerates the reviewed Phase-A trace and
Phase-B batching from source, then emits one overview and nine static
macro-layer SVGs. It preserves all 23 source operations, 60 PPMs/outcomes, 60
conditional frame updates, 36 source dependencies, 12 candidate memberships,
and 1,584 cross-level pair certificates; layers 2, 8, and 9 remain visible even
though they contain no PPMs. Every document visibly and mechanically uses
`candidate_batch_level_not_time` and separates the general logical candidate
from the rejected finite backend.

The independent atlas replay imports neither renderer, compiler, nor scheduler.
It rebuilds the displayed projection from serialized inputs, parses all ten
SVGs as XML, and checks one-time SVG coverage of 23 source IDs, 60 PPM IDs, and
60 update IDs. Fourteen focused tests, 52 combined Phase-A/Phase-B/atlas/Hub
tests, Ruff, strict mypy on 49 source files, compileall, and 14-artifact direct
hash determinism pass. Full pytest reports 276 passes plus the same two known
unrelated sibling-pin failures. Manual raster QA caught and fixed palette,
portable-glyph, and frame-out clipping defects before submission. See
`docs/DIRECT_CCZ_PPM_ATLAS_CONTRACT.md` and
`coordination/reviews/T-20260901-008.md`.

This is a `NUMERICAL` audit projection. It adds no native construction,
surgery-round, runtime, physical-qubit, or failure result.

The reviewer independently reconstructed every displayed count from the raw
Phase-A/Phase-B JSON with scripts that import neither the atlas builder nor
the renderer nor the repository's own replay module -- including a
regex-based SVG scan as a genuinely different parse method from the reviewed
module's XML-based one -- and got exact matches throughout (60 PPM-to-batch
memberships, 186 within-batch pairs, 1,584 cross-level certificates with the
full non-exclusive reason tally, and complete 23/60/60/36 source/PPM/
update/dependency coverage). The reviewer also specifically isolated the 378
`deterministic_frontier_partition`-only pairs and confirmed from the raw
relation table (not the doc's prose) that every one is independently marked
compatible, directly substantiating the "not a physical conflict" claim.
Artifacts were regenerated twice with independently-computed byte-identical
hashes, and four structurally distinct panels (overview, densest, PPM-free,
multi-batch) were rasterized and visually inspected with no clipping or
legibility defects found.

`T-20260901-007` is `RV-20260901-006` `APPROVED` (Claude review, 2026-09-01).
The exact Phase-B classifier profiles all 60 presented PPMs and all 1,770
pairs. It finds zero branch-possible-Y PPMs, 30 nonzero symplectic
commutators, 30 per-index axis-conflict pairs, 1,206 causally ordered pairs,
1,116 reaction-connected pairs, and six compatible pairs with shared logical
support. Exact ready-frontier splitting produces 12 unitless candidate levels
of sizes 12, 12, 6, 6, then eight groups of 3. Both the causal-path and
conflict-clique lower bounds are 12, so the construction is optimal only
inside the documented logical candidate model. Peak demand in the stated
semantic-liveness coordinate is 26 logicals/four live CCZ resource states, and
maximum presented PPM weight is seven.

General candidates, finite-instance admission, and low-rate fallback are
separate artifacts. The finite schedule/runtime/physical-qubit/failure fields
are null: 13 capability fields and 13 backend fields remain missing, three
bb18 factory values are incompatible with the selected domain, and four
native-mapper obligations are absent. The low-rate artifact is a 60-PPM
semantic singleton order with finite cost `OPEN`. Measured-product rewrites
and selective Clifford materialization were screened with zero admitted
transforms. The independent verifier imports neither compiler nor scheduler
and reconstructs every relation, dependency/reaction closure, liveness count,
lower bound, output class, and strategy row from serialized dictionaries. See
`docs/DIRECT_CCZ_PPM_BATCHING_CONTRACT.md` and
`coordination/reviews/T-20260901-007.md`.

The reviewer independently reimplemented the entire DAG-closure and relation
model from scratch, matching every claimed count exactly after catching and
fixing a bug in the reviewer's own first attempt (a nominal-support-vs.
frame-corrected-presented-support mismatch in the compatible-pair count),
independently re-validated the actual 12-level schedule end to end with zero
compatibility or causality violations found, and independently re-derived the
peak liveness figures from the contract's stated rule.

The number 12 is not surgery depth, a duration, or a finite-backend schedule.

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

`T-20260901-008` renders the reviewed decisions from the same machine-readable
trace and candidate artifacts and is `RV-20260901-007` `APPROVED`.
`T-20260901-009` reuses the compiler for IP-QCLA without the existing seven-T
route and is `RV-20260901-008` `APPROVED`.
`T-20260901-010` now separates exact-anchor width scaling from the still-open
compatible finite-backend integration and is `RV-20260901-009` `APPROVED`.

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

0. `T-20260906-003` is approved (`RV-20260907-002`). `T-20260906-004`
   (unassigned) is now the next executable task: re-evaluate width-256
   OOP-QCLA structural demand using only the now-verified commutation-aware
   rules, reporting exact logical demand, macro-depth, candidate levels,
   support/multiplicity/contact envelopes, and live-value demand with
   deterministic independent replay; all native cycles, seconds, physical
   qubits, and failure outputs must remain null.
1. Source or compute a `d1=17,d2=27` output/transport/consumer
   error model and a finite decoded buffer/reaction contract before connecting
   the AutoCCZ adapter to width-256 QCLA demand.
2. Add factory service, finite buffer, routing, and backlog to the width-256
   adaptive-PBC T-demand series as a separate, comparison track; report stalls
   separately from the current ideal-supply timeline.
3. Implement one coherent native mapper and finite backend that can admit the
   now-certified 34/68 width-256 logical candidate levels from
   `T-20260903-001`, together with the branch-dependent support hypergraphs
   from `T-20260903-002` (either a mapper that handles branch-dependent
   support directly, or an explicit frame-materialization policy). Do not
   treat those levels as surgery rounds while physical support, routing,
   timing, capacity, decoder/reaction, and factory service are open; no task
   ID is claimed for this yet.
4. Human records the `T-BOOT-001` full-ECDLP circuit choice before project-wide
   `T-BOOT-002` is claimed.

## Known risks

- `R-20260901-005` proves 12-level optimality only inside the explicit logical
  candidate model. Bounded-degree construction, distance preservation,
  physical support, routing, decoder service, and finite capacity are `OPEN`;
  no reviewer should relabel candidate levels as surgery rounds.
- The six compatible overlapping pairs establish that overlap alone is not a
  conflict under the screen; they do not establish a backend construction for
  overlapping physical supports.
- Product rewrites and selective frame materialization have zero admitted
  transforms. Their screened counts are opportunities, not validated savings.
- The logical peak of 26 uses the documented semantic-layer/just-in-time-clean
  coordinate; it is neither a physical-qubit total nor a finite memory plan.
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

No task currently holds an active lock in `coordination/WORK_LOCKS.md`; every
row is `RELEASED`.
