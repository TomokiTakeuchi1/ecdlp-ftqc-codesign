# H-tracked / bare-CNOT parallel low-rate surgery cycle

Task `T-20260927-001`; experiment `E-20260927-001`. Canonical generation is
complete; task IN_REVIEW, `RV-20260927-001` PENDING with claude. Results below
await independent cross-review.

## Question

Profile the reviewed width-256 in-place modulo-`2^256` QCLA when both target-H
layers of every direct-CCZ macro are Clifford-frame tracked, while each explicit
source-CNOT layer is executed as a bare logical operation. This closes the gap
between the logical H-tracking profile in `T-20260909-001` and the finite-capacity
parallel low-rate backend in `T-20260926-001`.

No completed prior cycle combines these two choices. `T-20260909-001` reports
mixed-axis support and frame growth but no low-rate schedule; `T-20260926-001`
profiles full H/CNOT tracking; and `T-20260926-002` profiles conjugated H with
bare CNOT/X.

## Exact policy

Use the convention `physical = F ideal`.

- A tracked desired H applies no physical H and updates the frame according to
  `F_out = F_in H_T`, with the exact joint direct-CCZ macro semantics replayed
  rather than inferred from a post-processed support table.
- A bare source CNOT `U` is applied logically and updates
  `F_out = U F_in U^dagger`.
- The primary source-X policy is bare/cheap logical X, matching the reviewed
  H-tracking profile. A Pauli-frame-X sensitivity may be added, but it must be
  separately identified and must preserve the reviewed X-layer dependency
  barriers.
- The four IP source-CNOT layers contain `256, 255, 254, 254` CNOTs. They remain
  explicit service obligations even if a later code realizes each pattern as
  one addressable automorphism call.
- Input preparation and final-frame materialization are excluded from the
  kernel comparison for every policy; final frame size and support remain
  explicit downstream obligations.

## Compiler and semantic gates

The new trace must retain all signs, X/Y/Z axes, six raw outcomes per direct-CCZ
event, resource identities, source barriers and the reviewed 30-macro order.
An independent replay must reconstruct every presented PPM and final frame.
Width-5 dense channel anchors must reject incorrect H placement, frame order,
CNOT conjugation, branch signs and resource reuse.

The width-256 demand remains 2,458 direct-CCZ events, 14,748 PPM/readout records,
30 macros and a peak of 255 fresh CCZ states. These are regression targets, not
new results. The existing 60 candidate phases are dependency levels, not
surgery rounds.

## Low-rate lowering and capacity sweep

Reuse the reviewed low-rate primitives and service accounting from
`T-20260926-001` without changing their interpretation:

- QWC mode uses deterministic source-order first-fit packing;
- general mode uses direct QWC measurement when possible and otherwise the
  reviewed regularized commuting-measurement gadget;
- constraints are applied after lowering: simultaneous executed-PPM count `K`,
  individual executed weight `W`, and summed support `S`;
- the initial grid uses `K = 1, 4, 16, 64, 256, unlimited`,
  `W = 16, 32, 64, 128, 256, 512, unlimited`, and the reviewed `K=64`
  summed-support sensitivities `S = 512, 2048, 8192`;
- use the same 64 hashed branches plus forced all-zero/all-one witnesses and the
  same service inputs `1/0.25/0.25/0.1` for surgery/preparation/readout/reaction
  with 64 preparation/readout lanes;
- any 512-hash refinement must be selected by a declared deterministic boundary
  rule and must not be described as a probability estimate.

The tracked-H frame is real, so any Y-containing presented Pauli should retain
even Y parity. This must be checked rather than assumed; an odd-Y witness must
trigger the already-defined catalyst accounting or fail closed.

## Required outputs

For every branch, mode and capacity cell, record separately:

- coupling-surgery batches and executed-PPM counts;
- preparation, resource-readout and reaction services;
- executed individual-weight and summed-support maxima;
- QWC splits or general-gadget ancillas;
- Y-containing and odd-Y PPM counts;
- the four bare-CNOT source layers, without silently assigning them zero time;
- CCZ burst demand and service timestamps;
- final-frame size/support and excluded materialization obligation;
- feasibility status and exact rejection reason.

Report a symbolic automorphism adapter

```text
T_complete = T_low_rate + sum_l a_l * tau_auto(l) + T_X
```

where `a_l` is the number of native automorphism calls needed for source-CNOT
layer `l`. The optimistic sensitivity `a_l = 1` is allowed, but it is not a
code-specific addressability claim. Also report the branch-paired maximum
additional CNOT/X service that preserves an advantage over the approved full-
tracking and conjugated-H baselines.

### Precise comparison and timing boundary

CHECK: `T_complete` above means the complete **kernel** after adding source
Clifford service, not initialization, final-frame materialization or full
arithmetic/ECDLP runtime. All services are serial in this comparison; a native
implementation with overlap requires a newly validated combined schedule.
Each automorphism duration must cover its preparation, routing, readout and
controller service as applicable, rather than an unqualified unit gate time.

Write `B_hybrid = sum_l a_l * tau_auto(l) + T_X`. For each COMMON-PPM-feasible
branch and cell, full tracking supplies the threshold
`B_hybrid < T_full_low_rate - T_hybrid_low_rate`. Signed zero/negative thresholds
are retained; they cannot support a strict win with nonnegative added service.
The four-equal-call sensitivity additionally sets `a_l=1` and `T_X=0`, yielding
`tau_auto < delta/4` at width 256, not an admitted automorphism duration.

Against conjugated H, the complete reference also has unknown service
`B_legacy`. The correct condition is
`B_hybrid - B_legacy < T_legacy_PPM - T_hybrid_low_rate`.
This is NOT an absolute hybrid budget and does not price legacy H/CNOT at zero.
Retained output frames can differ and stay outside both kernels. Nearest-rank
quantiles are taken only AFTER pairing on each cell's common feasible subset;
QWC/general subsets may differ. Forced witnesses never enter quantiles.

PROVED (under the fixed six-bit branch convention and gate set): switching a
source X between bare action `X F X` and virtual action `F X` can change signs,
but not the symplectic X/Z support action of the frame. Subsequent Clifford
updates and fixed-branch corrections preserve that property. Thus the two X
policies have equal PPM axes/weights and fixed-model service counts; signs and
final frames must nevertheless be independently replayed. The frame-X case
has zero additional physical source-X operation service, with controller work
still included in the explicit reaction assumption.

The first checkpoint uses 64 hashes plus the two forced branches only. No
512-hash refinement, population probability or universal dominance is claimed.

### Relation to the full-tracking frame

PROVED (same source order and raw branch bits): let G be the chronological
product of the physical source Cliffords already executed by the hybrid policy
(CNOTs, plus Xs only in bare-X mode). Then `F_hybrid = G F_full`. It holds at
identity entry. A common tracked H or branch correction right-multiplies both
frames. At a bare source U, `F_hybrid' = U G F_full U^dagger`, whereas
`F_full' = F_full U^dagger`, so `G' = U G`. Consequently corresponding PPMs
obey `P_hybrid = G P_full G^dagger`, including signs and fresh unframed resources.
The retained final frames obey the same relation.

PROVED: because G contains only CNOT/X, its action preserves the bilinear form
`x_i dot z_j` over GF(2). It does not preserve individual weight, summed
weight, or qubit-wise commutation. Thus bare CNOT is not guaranteed to reduce
PPM support or QWC packing depth. When both policies take the general-gadget
path on the same macros, the fixed bilinear regularizer has the same generator
combinations/groups; with no weight/sum-support caps their stage cardinalities
and services at the same K agree. A change in the direct-QWC fast path or a
finite support cap can change that conclusion. This is a conditional structural
explanation, not a universal ordering of physical surgery constructions.

NUMERICAL anchors: the prefix relation (all signed PPMs and final images) and
bilinear-form identity are checked on widths 2, 5 and 8, both X policies and
four branch witnesses. Width-5 actual shared-control and shared-target macros
are checked densely over all 4,096 outcome combinations each after an incoming
bare CNOT; an incorrect opening-H convention fails the negative control.

## Interpretation boundary

The cycle may establish a reproducible logical/conditional-service profile and
identify where bare CNOT avoids tracked-frame support growth. It must not claim
that an HGP/LP code supplies the required addressable automorphisms, that one
automorphism call is constant physical time, or that logical support is a
connected physical surgery representative. Native cycles, milliseconds,
physical qubits, routing, decoder throughput, factory realization and failure
probability remain null until one compatible code/architecture contract closes
them.

## Acceptance checkpoint

The first checkpoint is complete when the signed hybrid trace, independent
semantic replay, QWC/general finite-capacity grid, four-layer bare-CNOT service
separation, branch-paired baseline comparison, deterministic artifacts and
focused regression tests are ready for cross-review. Any result stronger than
that requires a separately reviewed native automorphism mapper.

## First checkpoint results (2026-09-27)

NUMERICAL: 64 hashed and two separate forced branches are complete. Each branch
contains hybrid bare-X, hybrid frame-X, full-tracking and conjugated-H/bare-source
traces. Independent signed-history audits cover 1,946,736 coupling PPMs in total
(973,368 in the two new hybrid policies). The saved grid has 441 policy/mode/
capacity cells per branch and 504 paired comparisons: 29,106 and 33,264 rows
respectively. Aggregate coverage, nearest-rank quantiles and every cost/delta
are independently checked with exact rational arithmetic.

The source regressions remain 2,458 CCZ states, 7,374 coupling PPMs plus 7,374
resource readouts, 30 macros, 255 peak held CCZ states and 1,007 source values.
CNOT layers at source layers 2/19/21/38 have 256/255/254/254 gates. The 510
source X gates are bare in the primary policy and virtual in the sensitivity.
Both X policies have identical axes, weights and fixed-model services for all
66 branches, although their signs and final frame records can differ.

### Unbounded-support comparison

NUMERICAL: these are nearest-rank medians on the same 64 hashed branches;
forced branches are excluded. CHECK units use 1/0.25/0.25/0.1 for surgery,
logical-zero preparation, readout and reaction, with 64 preparation/readout
lanes. Hybrid units omit the unknown CNOT/X service; legacy units omit all
unknown conjugated-H/source-Clifford service.

| Policy | Mode | K | Surgery steps p50 | Low-rate service units p50 |
|---|---|---:|---:|---:|
| Hybrid H-tracked / bare CNOT | QWC | 64 | 305 | 339.5 |
| Full tracking | QWC | 64 | 296 | 330.5 |
| Hybrid H-tracked / bare CNOT | General | 64 | 263 | 359.5 |
| Full tracking | General | 64 | 263 | 359.5 |
| Hybrid H-tracked / bare CNOT | QWC | 256 | 263 | 297.5 |
| Full tracking | QWC | 256 | 254 | 288.5 |
| Hybrid H-tracked / bare CNOT | General | 256 | 119 | 216 |
| Full tracking | General | 256 | 119 | 216 |
| Hybrid H-tracked / bare CNOT | QWC | unlimited | 258 | 292.5 |
| Full tracking | QWC | unlimited | 249 | 283.5 |
| Hybrid H-tracked / bare CNOT | General | unlimited | 104 | 201 |
| Full tracking | General | unlimited | 104 | 201 |
| Conjugated H / bare CNOT/X (PPM only) | QWC | 64 | 126 | 160.5 |
| Conjugated H / bare CNOT/X (PPM only) | QWC | 256 | 40 | 74.5 |
| Conjugated H / bare CNOT/X (PPM only) | QWC | unlimited | 30 | 64.5 |

CHECK: the actual branch-paired `delta = T_full - T_hybrid` must be used rather
than subtracting the displayed marginal medians. QWC delta medians at
K=1/4/16/64/256/unlimited are 0/-1/-4/-6/-7/-7 units. At K=64 the range is
[-34,4], with 57 negative, 2 zero and 5 positive witnesses. Thus a hypothetical
four-equal-call, zero-X-cost implementation has at most 1 unit per call even
on the best witness of that cell; most witnesses allow no strict advantage.

NUMERICAL: general service counts agree branch by branch for every hashed
witness at all six K values when W/S are unlimited. Its delta is exactly zero,
not merely a coincidence of medians. Positive additional CNOT service then
makes the hybrid slower in this serial kernel model. This is NOT universal
dominance: the forced all-zero branch at K=64 has delta 45.4 (general) / 2
(QWC), and finite summed-support limits can reverse individual comparisons.

### Finite support and boundary witnesses

NUMERICAL: executed weight p50/max over the 64 hashes is hybrid QWC 275/443,
hybrid general 273/370, full QWC 270/446, full general 261/376, and legacy
116/190. The primary/sensitivity hybrid values coincide. All presented PPMs
have even Y parity; the peak extra logical gadget count is 765 for general,
zero for QWC, and no Y catalyst is needed. This is not physical ancilla counting.

At W=256, K=64, S unlimited, hybrid QWC/general each fit 24/64 witnesses,
versus full QWC 25 and full general 27. The common sets have 24 witnesses;
full-only counts are 1 and 3, hybrid-only counts zero. W=512 fits all hashes,
but not all-one: hybrid QWC/general maxima are 572/570, versus full 662/638
and legacy 509. All-zero hybrid maxima are 2/2, versus full 4/5. None of
these samples are population probabilities or guaranteed worst-case bounds.

CHECK: at K=64, W unlimited, S=512, the hybrid/full general medians are
397/400 surgery steps and 495/497.4 conditional units. The paired delta median
is **1**, not 2.4, with range [-8,11], 17 negative, 6 zero and 41 positive
hashes. The four-equal-call, zero-X-cost median allowance is therefore 0.25
units per call, but it is not sufficient for all branches. At S=2048 the
paired median is 0 (range [-4,3]); at S=8192 every hashed delta is 0.
Bare CNOT is therefore not automatically a runtime win, although cap-specific
savings exist. Geometry-specific representatives and endpoint materialization
could change a later physical comparison and remain OPEN.

## Reproduction

```text
.venv/Scripts/python.exe scripts/run_h_tracked_bare_cnot_low_rate_cycle.py --workers 4
.venv/Scripts/python.exe scripts/run_h_tracked_bare_cnot_low_rate_cycle.py --verify-samples 1
.venv/Scripts/python.exe -m pytest tests/unit/test_h_tracked_bare_cnot_low_rate.py -q
```

Outputs: `experiments/runs/T-20260927-001/summary.json`, 66 deterministic gzip
artifacts with four signed traces, lowerings and representative PPM-only
timelines, plus source/config-bound checkpoints. Summary SHA-256:
`2ef25c5ce205e94732ecb83c304fa8be14301ee27d086c714ea18094d4a27e48`.
Base commit `b30f42d8f8e70cebf6ac59e7feff8fd523fdf3e9`; exact computational
hashes and seed are in the summary. Environment: Python 3.14.3, NumPy 2.5.2,
pytest 9.1.1. Generated files remain Git-ignored and must be regenerated.

Validation: 38 focused hybrid tests and 107 related tests pass. Full-suite
collection preceded five added hybrid cases: 487 passed and two known unrelated
sibling-pin failures in 963.45s; the five additional cases are covered by the
latest related run. Strict mypy passes 79 source files; scoped Ruff and
compileall pass. Fresh forced -2/-1 and hashed 0 artifacts/rows are byte-identical;
checkpoint resume reproduces the summary byte-for-byte. Every full/legacy
trace/lowering on all 66 branches and 1,980 common service cells agree with the
approved baseline. Cross-review remains PENDING, not APPROVED.
