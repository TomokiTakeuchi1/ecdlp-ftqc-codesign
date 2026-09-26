# Capacity-limited parallel low-rate surgery: first QCLA profile

Task T-20260926-001; experiment E-20260926-001. Primary workload IP modulo
2^256; OOP modulo 2^256 is the control. These are uncontrolled additions, not
prime-modular multiplication or full ECDLP.

## Logical contract

CHECK: all source wires remain resident from start to finish. Initialize source
scratch according to the reviewed circuit before entry; retain the full output
frame. No early scratch reset/release, transfer, source-preparation timing, or
output-frame clearing is inferred. Full source initialization and final decoding
are outside the timed kernel. Source X/CNOT layers remain ordering barriers.
Reviewed coherent joint-CCZ macro memberships are unchanged: OOP 15, IP 30.

PROVED (algebraic specification; implementation checked numerically): write
physical = F ideal. Track a Clifford U by F <- F U^dagger. The columns are
signed F X_j F^dagger and F Z_j F^dagger, represented as i^p X^x Z^z.
For each joint macro, track H once per distinct target, present ALL three
resource-data ZZ observables per event in the COMMON resulting frame, measure
fresh resource Xs, append diagonal Figure-14(a) corrections, and track the
closing H set. All six outcome bits enter the signed correction. No same-macro
correction changes another event's observable. All preceding macro outcomes
must be decoded before the next macro is submitted (conservative frontier).
Source H/CNOT physical gate cost is zero under this tracking policy, not under
the older conjugated-H/bare-CNOT policy. Existing old-policy weight bounds do
not apply. The fresh resources are unframed and globally uniquely named.

## Measurement macro specification

LITERATURE: Cowtan--He--Williamson--Yoder, arXiv:2503.05003v3 section 3.6,
and Zhang--Li, arXiv:2408.01339v3 appendix I.

- QWC mode: source-order first-fit batches. A logical qubit may be shared when
  all nonidentity axes agree. Mixed X/Z/Y and physical representative overlap
  are not intrinsically rejected; the construction still needs branching and
  compatible connectivity. No zero-cost physical overlap assertion is made.
- General mode: use direct measurement if the whole set is QWC, otherwise
  change the signed generator basis by invertible symmetric GF(2) congruence.
  Diagonal pivots and hyperbolic pairs partition it into at most two regular
  sets (x_i dot z_j = 0 for distinct rows of each set). Store every row's exact
  original-generator combination. Reconstruct original outcome bits by matrix
  inversion; signed products, not unsigned support, define this map.
- For each regular subset, implement the two-stage twist-free gadget, with a
  private |0> ancilla A and, for odd Y count, |Y+> catalyst B. The executed PPMs
  are X[x] X_A (X_B) and Z[z] X_A (Z_B), then destructive Z_A readout. For k Y
  terms and original sign s, recovered outcome is m1 XOR m2 XOR s XOR
  (ceil(k/2) mod 2). If Z_A=-1, the residual Pauli is Z[z] (Z_B). Its data part
  is tracked with exact anticommutation sign rebasing, and Z_B restores the
  catalyst. Catalyst preparation measures Y on a prepared |0>; a negative
  result is sign-normalized by a tracked Z. Preparation/reaction is charged.
  The profiler does not sample these auxiliary outcomes: they change signs,
  not weights/axes/durations under the stated fixed service model.
- Gadget Pauli corrections are virtual, not silently forgotten. The signed
  input trace is the canonical corrected coordinate; auxiliary byproduct
  effects on later measurement signs must be XOR-rebased before execution.
  Matrix instrument checks cover all auxiliary outcomes and catalyst states.
- Two/four MAIN measurement stages exclude preparation/final readout/reaction.
  Finite capacity can split each stage further. Anticommuting inputs are rejected.
  General mode is a fixed construction, not guaranteed faster than QWC packing.

## Capacity and service

CHECK: K limits simultaneous PPM count; w limits each EXECUTED PPM's logical
weight; S limits the sum of those weights, counting repeated occurrences.
Test after basis change and gadget expansion, including resources/auxiliaries.
The support UNION and maximum contact multiplicity are separate diagnostics.
Physical representative weight omega, physical ancilla count/check degree,
code distance, embedding, routing and circuit-level fault tolerance remain OPEN.
The paper's asymptotic space formulas are not converted to calibrated qubit counts.
The QWC axes refer to the selected logical basis; mapping that basis to the
construction's required code representatives can increase physical weights.

An overweight instruction returns infeasible_for_this_lowering, not a proof
that no synthesis or architecture can implement it. Products are never measured
factor-by-factor as a shortcut. The regularized basis is deterministic and not
weight-optimized. Whole-set regularization is performed before finite packing.

CHECK: each stage completes before the next; macros do not overlap. Every macro
reserves all its CCZ states at entry and keeps resource wires through final X
readout. Auxiliary |0> and readout lane counts are explicit independent inputs.
Each |Y> catalyst is freshly provisioned per macro; the conservative peak counts
all auxiliaries in that macro, without assuming cross-macro reuse. State release
after a restored, unentangled catalyst adds no extra timing beyond the declared
service model. All physical preparation/routing/teardown costs must be included
in a calibrated macro service before making native claims.

Output separately: surgery-only steps; preparation/readout/reaction steps;
conditional duration = Ns*t_surgery + Np*t_prepare + Nr*t_readout + Nc*t_reaction;
conditional seconds (only when seconds_per_unit supplied); peak resident logical
wire envelope; CCZ demand timestamps and held resource-state counts. The 1ms/unit
example is an arbitrary CHECK sensitivity, not neutral-atom or qLDPC timing.
Native cycles, native runtime, physical qubits and failure stay null. Factory
service/buffering, memory bandwidth and physical connectivity remain OPEN.
The reaction parameter must cover decoding, frame updates, outcome rebasing,
branch-dependent basis construction and scheduling/controller service. Python
profiling time is not a hardware latency. Constant macro durations within the
admitted support budget are CHECK assumptions; support-dependent physical graph
preparation and control latency need later code-specific calibration.

## Real-Clifford invariant

PROVED (under this gate set): H, CNOT, CZ, X and Z have real matrices, so every
branch frame F is real. Each input ZZ or resource X is real; F P F^dagger is
therefore a real Hermitian Pauli. An odd number of Y tensor factors would make
it imaginary, hence every presented PPM has even Y parity. Products of commuting
real Hermitian Paulis remain real Hermitian; the generator change preserves the
property. Consequently this workload never needs the odd-Y |Y> catalyst in the
stated general-commuting gadget. It can still have Y pairs, mixed axes and QWC
conflicts. This is not a claim for Clifford frames containing S, nor a physical
ancilla-free claim: |0> gadget ancillas and branching ancillas remain necessary.

## Validation and sampling

NUMERICAL: fixed SHAKE-256 seed supplies all six outcomes per source gate.
64 hashed branches and forced all-zero/all-one witnesses are kept separate.
Report nearest-rank sample summaries, not probabilities or guaranteed maxima.
Store trace/lowering and representative schedule records as deterministic gzip
JSON, plus all capacity-grid outcomes and input/source hashes. Generated files
are regenerated, never manually patched. Boundary refinement to 512 witnesses
is a separate generated refinement artifact under the same task if executed.
Integer bitmaps at least 2^53 are serialized as hexadecimal strings prefixed
with `0x`; this preserves sparse support and avoids huge decimal gzip payloads.

Independent reverse-history bit-sliced conjugation checks signed traces and
retained frames. A full-pair source dependency oracle checks frozen macro groups.
Dense matrices check every signed nonidentity Pauli up to three qubits across all
eight gadget outcomes, and arbitrary-frame direct CCZ across all 64 branches.
Independent replay checks signed generator products, basis invertibility,
regularity, packing coverage, QWC, constraints and accounting. Mutations must fail.

Cross-review completed: `RV-20260926-001` is `APPROVED` by claude on
2026-09-26, with no required changes. This approves the logical model and
conditional numerical profile, not a native QEC implementation or runtime.

## First-pass results (2026-09-26, Claude cross-review approved)

NUMERICAL: 64 hashed witnesses plus separate all-zero/all-one witnesses for
each variant. All 730,026 coupling-PPM instances pass signed independent replay.
The table uses nearest-rank p50 over the 64 hashed witnesses, with individual
weight and total support unlimited. Counts exclude destructive resource readout.

| Workload | K | QWC surgery steps | General surgery steps | QWC conditional units | General conditional units |
|---|---:|---:|---:|---:|---:|
| OOP | 64 | 92 | 111 | 109.25 | 149.75 |
| OOP | 256 | 59 | 49 | 76.25 | 87.75 |
| OOP | unlimited | 54 | 44 | 71.25 | 82.75 |
| IP | 64 | 296 | 263 | 330.50 | 359.50 |
| IP | 256 | 254 | 119 | 288.50 | 216.00 |
| IP | unlimited | 249 | 104 | 283.50 | 201.00 |

CHECK: conditional columns use surgery=1, zero preparation=0.25, destructive
readout=0.25, reaction=0.1, and 64 preparation/readout lanes. Medians in different
columns need not belong to the same branch. The optional 1ms/unit conversion is
only an illustrative input, NOT a code/hardware result. With these inputs the
general construction improves IP time at K=256/unlimited, but not at K=64;
for OOP, its extra service outweighs the surgery-stage reduction even at
unlimited K. This is a policy/parameter result, not optimality or a lower bound.

NUMERICAL: at K=64, S=512 changes median surgery steps QWC/general from 92/111
to 99/122 for OOP, and from 296/263 to 365/400 for IP. S=2048 gives 92/111 and
297/267; S=8192 gives 92/111 and 296/263. Sum support is not the support union.

NUMERICAL: maximum executed weight per hashed branch has these p50/max values:
OOP QWC 119/234, general 119/234; IP QWC 270/446, general 261/376.
An individual-weight cap 128 admits 38/64 OOP witnesses in either mode and no IP
witness. Cap 256 admits all 64 OOP witnesses and 25/64 (QWC), 27/64 (general) IP
witnesses. Cap 512 admits all hashed witnesses but NOT the all-one witnesses:
their QWC/general maxima are OOP 635/636 and IP 662/638. All-zero witnesses give
OOP 3/3 and IP 4/5. No sample statistic is a worst-case guarantee.

NUMERICAL (reviewer sensitivity check, RV-20260926-001 F4.2): reversing the
input order to the general regularization changes IP maximum executed weights
on hashed branches 0/1/2 from 267/290/220 to 251/260/229. Thus the weight-cap
admissions above depend on this deterministic, non-weight-optimized generator
choice; the observed changes include a roughly 10% reduction, not a universal
10% bound. The review reports unchanged main step counts on its tested cases,
not an invariance theorem for arbitrary regularizations or capacity limits.

NUMERICAL: maximum extra logical gadget-ancilla count across hashed witnesses
is OOP 216 and IP 765; QWC adds no logical gadget ancilla, but physical branching
ancillas are not counted here. Y-catalyst count is zero, consistent with the
real-Clifford invariant. All source wires and macro CCZ resources remain counted
in each representative timeline's conservative logical-wire envelope.

Validation: 26 latest focused tests pass; the full-suite run collected before
five final focused additions reports 411 passes and the same two pre-existing
sibling-HEAD pin failures. All unchanged regression files were included. Ruff,
strict mypy (Python 3.14 target matching installed NumPy stubs), and compileall
pass. Both boundary branches and hash branch 0 in each variant regenerate
byte-identically (six complete compressed artifacts); full 132-artifact repeated
byte comparison was not run. Every branch was independently audited at generation.

Environment: Python 3.14.3, NumPy 2.5.2, pytest 9.1.1, Ruff 0.16.3, mypy 2.3.0.
Starting HEAD b7aad59c50a4680aeac847c8e646219ec5df5eab plus preserved dirty
dependencies; exact computational source hashes are in generated summary.json.
The static SVG was rasterized with bundled sharp and visually checked.

Reviewer validation (claude, 2026-09-26): independent signed Stim replay of
10 width-256 traces, dense multi-event macro/gadget checks, and content audits
of all 132 artifacts reproduce the reported grid cells and summaries. Four
additional representative artifacts regenerate byte-identically. The reviewer
reran the 26 focused cases; the review records 416 full-suite passes and the
same two known sibling-pin failures. These are reviewer results, separate
from the earlier implementer run above. See coordination/reviews/T-20260926-001.md.

Reproduce from the repository with `.venv/Scripts/python.exe`:

```
scripts/run_parallel_low_rate_cycle.py
scripts/run_parallel_low_rate_cycle.py --verify-samples 1
-m pytest tests/unit/test_parallel_low_rate.py -q -p no:cacheprovider
```

Outputs: `experiments/runs/T-20260926-001/summary.json`, `capacity-map.svg`,
per-branch gzip JSON, and `reproduction/validation.json`. The PNG is a derived
preview of the SVG, not a canonical numerical artifact.

OPEN follow-up: pin both versioned source PDFs with SHA-256 in the literature
corpus (non-blocking review request F4.1, not completed by this status update).
Macro/semantic cross-review is now approved; the proposed feasibility-boundary
refinement to 512 hashed witnesses has NOT been run. Then calibrate
support-dependent surgery, ancilla preparation and controller service with
the low-rate surgery collaborators before claiming physical runtime.
