# Paired Clifford-cost break-even on parallel low-rate surgery

Task T-20260926-002; experiment E-20260926-002. Review RV-20260926-002
APPROVED by claude, 2026-09-27; task DONE. Native costs remain OPEN.

## Scope and comparison

CHECK: compare the same uncontrolled modulo-2^256 OOP/IP additions, frozen
15/30 CCZ macros and source barriers, resident logical values, six-bit
branch assignments and serial service conventions. Full H/CNOT tracking
uses the approved T-20260926-001 compiler. The legacy comparator uses
conjugated H and bare source CNOT/X, NOT an executable high-rate backend.
Both use the same parallel low-rate QWC primitive. Tracked general-commuting
lowering is also evaluated; legacy Z-only inputs already have direct QWC
lowering, so its general mode would coincide with that primitive.

## Exact legacy semantics

PROVED (algebraic specification; implementation requires independent replay):
physical = F ideal. A bare source Clifford U retains F_out = U F U^dagger.
At each joint macro, fix the entrance frame F and distinct-target H product H_T.
Both physical H layers are G = F H_T F^dagger using THAT SAME entrance frame.
Between them present all F Z_j F^dagger Z_resource PPMs in a common frame.
The branch injection is proportional to F D V H_T, where V is the product of
CCZ gates and D is their complete six-bit diagonal byproduct. Applying the
closing G gives F H_T D V H_T = (F H_T D H_T)(H_T V H_T).
Thus the outgoing byproduct is F H_T D H_T. Conjugating the closing H by F D
instead would define a different policy, not the reviewed legacy baseline.
No correction from an event may alter another same-macro coupling observable.

PROVED: admitted macro targets are never controls in the same macro; H_T D H_T
contains only CNOT/CZ/X/Z. Bare source CNOT/X conjugation preserves this real
monomial subgroup. Hence every legacy coupling is signed Z-only; signs and
all six outcomes are retained, not only the support-changing bits.

## Cost and endpoint contract

CHECK: for a fixed branch and capacity/service configuration,

    T_legacy_complete_kernel = T_legacy_PPM + B
    B_crit = T_tracked_kernel - T_legacy_PPM

where B >= 0 is ALL additional legacy physical-Clifford service, including
conjugated-H realization, bare source CNOT (and any required source-X service),
ancilla preparation, extra measurement/readout, correction and controller
latency not already charged in the common PPM kernel. No physical Clifford
cost or feasibility is inferred from a candidate logical H layer.
If B < B_crit legacy is faster; if B > B_crit tracking is faster; equality ties.
A negative B_crit means no nonnegative B makes this legacy policy faster.
These statements require BOTH PPM lowerings to fit and a realizable legacy
Clifford service respecting the same resources. PPM feasibility alone does
not admit the complete legacy implementation.

Record signed differences of surgery/preparation/readout/reaction counts as
well as conditional units. No overlap between these services or B is assumed.
All input preparation and FINAL retained-frame materialization are excluded
for BOTH policies. Their different output frames remain explicit obligations;
this is a kernel comparison, not a complete downstream arithmetic comparison.
CCZ supply is ideal; factory delivery, buffers, physical representatives,
branching space, memory transfers, routing and failure remain OPEN.

## Paired witnesses and capacity

NUMERICAL protocol: reuse the reviewed seed T-20260926-001-full-frame-v1 and
logical-event-indexed six raw injection bits. Evaluate hashes 0..63 plus
separate forced all-zero/all-one per variant. Pair BEFORE aggregating; never
subtract unrelated medians or condition each policy on a different branch set.
Record both-feasible, tracked-only, legacy-PPM-only and neither-feasible counts.
No finite budget is emitted outside the intersection. Summed support counts
term occurrences, not union; K and logical weight are model inputs, not paper
variables or calibrated hardware limits. Limits apply after gadget expansion.

CHECK: refinement cells are selected deterministically from the initial
hashed sample by the manifest rule (partial joint feasibility or a budget-sign
boundary). Only those cells extend to 512 hashed witnesses. This conditional
selection is disclosed; no probability, confidence interval or exhaustive
maximum follows. Forced witnesses remain excluded from quantiles.

CHECK: general-commuting lowering retains the reviewed regularization order.
Its maximum executed weight, and therefore a weight-cap admission, can change
under another valid generator choice (RV-20260926-001 F4.2). No regularization
optimization or order-independent feasibility theorem is claimed here.

### How to interpret the budget

CHECK: B is a total elapsed-time allowance, not time per H or per CNOT. A
candidate conjugated-H layer can itself require multiple surgeries and
ancillas. Overlap between B and PPM service is excluded in this model; a
future overlapping implementation must compare a complete new schedule.
Negative Bcrit rules out a legacy win under nonnegative B; a positive sampled
median does not guarantee a win on every branch. Tracked-only and legacy-PPM-only
cells establish a feasibility difference between the chosen PPM lowerings, not
a complete architectural winner. Store the four integer service coefficients
of each branch so preparation/readout/reaction sensitivities remain explicit.

PROVED within this service model: for QWC-versus-legacy-QWC, both policies have
zero extra logical preparation stages, the same CCZ-resource readout counts
at the same lane capacity, and one reaction barrier per common macro.
Consequently delta_prepare = delta_readout = delta_reaction = 0; Bcrit is
exactly the difference in surgery-step counts times the surgery duration.
This cancellation does not apply to the general-commuting gadget comparison.
It also does not cancel any service belonging to the unknown legacy B.

CHECK: B may itself depend on the branch because the conjugated-H realization
depends on its entrance frame. A future calibrated comparison must pair
B(branch) with Bcrit(branch) before aggregating the complete time difference.
Comparing median B with median Bcrit alone is not a valid decision rule.
At restrictive weight caps, the common-feasible subset can also differ between
tracked QWC and tracked general. Their two displayed budget medians each give
a valid comparison with legacy on that mode's subset, but are not themselves
a branch-paired QWC-versus-general comparison. The unrestricted table below
does have the same 64 branches for both modes.

## Validation and outputs

Independent reverse-history signed replay must reconstruct the legacy trace,
source plan, branches and retained frame without importing its compiler.
Small dense channel tests check physical H placement and all outcome branches.
Packing/lowering/service audits reuse the approved independent verifier;
paired-status and summary checks independently recompute every threshold.
Mutation tests reject phase, frame, branch-pairing, count and budget corruption.
All native time/space/failure outputs remain null. Cross-review RV-20260926-002
is APPROVED (claude, 2026-09-27), with no required changes.

## Initial 64-hash checkpoint

NUMERICAL: all 132 initial OOP/IP branch instances (64 hashes plus two forced
per variant) passed signed history, alignment, lowering and resource audits.
The predeclared selector requests exactly 18 refinements: IP, weight 256,
both modes, all three K and S values. No initial cell has a negative budget;
this is a sample observation, not a proof over all possible branches.

CHECK: the following cells have unbounded individual and summed support,
with service durations surgery/preparation/readout/reaction = 1/0.25/0.25/0.1
and 64 preparation/readout lanes. Times are conditional units, NOT milliseconds
or QEC cycles. These unrestricted cells retain 64 hashes under the selector.
Each Bcrit is computed on a paired branch before its median is taken.

| Variant | K | Legacy PPM time | Tracked QWC time | Tracked general time | Median Bcrit QWC / general |
|---|---:|---:|---:|---:|---:|
| OOP | 64 | 80.25 | 109.25 | 149.75 | 29 / 69.5 |
| OOP | 256 | 37.25 | 76.25 | 87.75 | 39 / 50.5 |
| OOP | unlimited | 32.25 | 71.25 | 82.75 | 39 / 50.5 |
| IP | 64 | 160.5 | 330.5 | 359.5 | 170 / 199 |
| IP | 256 | 74.5 | 288.5 | 216 | 214 / 141.5 |
| IP | unlimited | 64.5 | 283.5 | 201 | 219 / 136.5 |

NUMERICAL: the uncharged legacy obligations are 2,458 conjugated-H target
applications in 30 candidate H layers and 766 source CNOTs for OOP; IP has
4,664 target applications in 60 candidate H layers, 1,019 source CNOTs and
510 source Xs. Candidate H layers are NOT native executable layers. The
resident/active source values are OOP 1,008 and IP 1,007, separate from fresh
CCZ resources and gadget ancillas. No missing Clifford cost is filled in.

NUMERICAL boundary witnesses (excluded from all hashed quantiles): all-one
legacy maximum weight is 509 for both variants, versus tracked QWC/general
635/636 (OOP) and 662/638 (IP). Thus with weight 512 and unlimited summed
support, only the legacy PPM portion fits; its physical Cliffords are still
unadmitted. In the all-zero OOP witness with unlimited K/support, Bcrit is
zero for both tracked modes. Positive hashed medians do not describe every
branch and cannot establish uniform legacy-policy dominance.

## Completed boundary refinement

NUMERICAL: the 18 preselected IP/weight-256 cells now contain hashes 0..511.
For each K/S setting, legacy PPMs fit 512/512 witnesses; tracked QWC fits
218/512, and the fixed tracked-general lowering fits 179/512. The remaining
294/333 respectively are legacy-PPM-only, with no finite Bcrit assigned.
The sample maximum executed weights over these IP hashes are legacy 242,
tracked QWC 466 and tracked general 413. Other capacity cells remain on their
initial 64 hashes; no unselected grid cell is inferred from the refinement.

NUMERICAL: the initial 64-hash admission ordering (QWC 25, general 27) reverses
in this extended witness set (218, 179). This is not a probability estimate,
nor a fundamental limit of general-commuting measurement: the selected
regularization/gadget policy is fixed and is not an optimized QWC/general
fallback. Its support threshold is order-sensitive, as noted above.

CHECK: at K=64 and unlimited S within the refined w=256 cells, median Bcrit
is 159 units on the 218 QWC-common branches and 199.5 on the 179 general-common
branches. These have DIFFERENT conditional branch subsets. The unrestricted
64-hash medians remain 170/199; none should be substituted for another cohort.
No tested hashed budget is negative. All-zero OOP still supplies a zero-budget
boundary witness, and the all-one branches retain their separate support caps.

NUMERICAL: all 580 branch/variant instances contain 8,067,156 independently
replayed coupling PPMs across both policies. The standalone exact-rational
saved-output audit validates all 580 artifact hashes, 15,192 paired rows and
234 initial/refined/final aggregate records. All 108 plotted cell labels
match saved data; the rendered four-panel map was visually inspected.

## Reproduction

CHECK: working tree based on a4dba72892c6736dac75357f039383b4d63bd2cc; experiment
E-20260926-002. Canonical source hashes, manifest, Python/NumPy/pytest versions,
PDF pins, branch identities and signed artifacts are stored in the generated
summary. Source/config-bound checkpoints reject stale resumptions or changed
artifact bytes; a failed job can be resumed with the same command.

```text
.venv/Scripts/python.exe scripts/run_low_rate_break_even_cycle.py --workers 4
.venv/Scripts/python.exe scripts/run_low_rate_break_even_cycle.py --verify-samples 1
.venv/Scripts/python.exe scripts/audit_low_rate_break_even_outputs.py
.venv/Scripts/python.exe -m pytest tests/unit/test_low_rate_break_even.py tests/unit/test_low_rate_break_even_cycle.py -q
```

The output directory is `experiments/runs/T-20260926-002/`. `initial-grid.json`
and `refinement-selection.json` precede the final `summary.json` and
`clifford-budget-map.svg`. Per-branch compressed artifacts contain both signed
traces, final frames, lowerings and representative K=64 unbounded-support
schedules. Legacy CCZ demand timestamps use **PPM-only** time: they cannot be
used as a complete factory demand schedule without inserting the unknown B.
The PDFs and generated artifacts remain Git-ignored, as in prior cycles.

CHECK: the manifest's example rates are decimal rationals (1, 1/4, 1/4, 1/10).
Integer service counts and rate inputs are authoritative, retaining full
precision. `exact-cost-audit.json.gz` additionally stores every cost and paired
budget as an exact [numerator, denominator], independently checks the normalized
floating display against the correctly rounded rational value, and recomputes
all saved quantiles and refinement selections from persisted data. The floating
display columns are not a claim of native clock precision or of resolution
below 1e-12 units for arbitrary future service calibrations.

Validation: 38 focused tests; latest focused + Hub 43 passed in 12.50s,
including exact-rational and native-summary mutation checks added after
full-suite collection. Full suite: 454 passed, two known unrelated sibling-pin
failures (2236.52s). Ruff, compileall, and strict mypy with the Python 3.14
target (78 source files including both scripts) pass. Environment: Python
3.14.3, NumPy 2.5.2, pytest 9.1.1. All 132 initial tracked artifacts/lowerings
and 3,960 shared grid entries agree with the previous approved cycle.
Seven complete branch artifacts freshly regenerate byte-identically: OOP/IP
-2, -1, 0 and refined IP 511. Checkpoint-resumed summary/SVG are also
byte-identical (this second check is NOT a fresh regeneration of all 580
traces). `RV-20260926-002` is APPROVED by claude (2026-09-27), with no required
changes. The reviewer independently recomputed 24 signed policy traces and
every grid entry of all 580 artifacts, and regenerated four additional
artifacts byte-identically. Review acceptance does not calibrate the unknown
legacy Clifford service or admit a native runtime comparison.
