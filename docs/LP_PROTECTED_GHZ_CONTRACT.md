# Protected LP masking for GHZ preparation

- Task: T-20261001-004; owner: codex; status: DONE.
- Review: RV-20261001-004, APPROVED by claude on 2026-10-01; no required changes.
- Input: E-20261001-004; starting HEAD e3a84d85c023d6d0e1377eb4a117b50fd24e2953.
- Scope: one completed LP instance, 300 canonical GHZ4 states; no arithmetic
  runtime, T/i-state factory, decoder, or circuit-noise simulation.

## Outcome and evidence boundary

NUMERICAL: a two-stage LP mask construction replaces the previous distance-one
measurement helper. Both the 9,600-qubit full code and the 9,075-qubit mask
have no weight-one or weight-two logical X or Z errors. This certifies only
`d_X,d_Z >= 3`, not their exact distance and not circuit-level fault tolerance.

NUMERICAL: the mask fixes 900 unwanted canonical Z modes and 38 residual Z
modes of a full-size auxiliary. The resulting auxiliary measures exactly
300 desired canonical X modes and two canonical-central residual X modes
of the data. The approved automorphism then produces the same 300 GHZ4s.

OPEN: FT uniform-state preparation, check extraction, decoding, noisy readout,
frame reliability, target-distance scaling, hardware mapping, total physical
footprint, failure budget and native runtime. This is a protected-code/ideal
channel result, not a completed fast factory.

## Construction and CNOT direction

Use the unchanged canonical section and binary conventions from
`LP_GHZ_HOMOMORPHIC_PREPARATION_CONTRACT.md` and the approved constructor.
Let `Q = LP(tilde_A,A*)`, lift 75, with 1,240 logical modes: 1,200 canonical
and 40 residual. The desired canonical first-factor index is i=4 one-based;
the associated information column is p=6 zero-based.

Delete only column p=6 of the 10-by-14 completed seed to form B (10-by-13):

`M = LP(B,A*)`.

The coordinate injection iota from M into Q keeps all first-summand cells
except p=6 and all second-summand cells. It removes the contiguous physical
strip R = [3150,3674], 525 qubits. Denote its complement by S.

PROVED: the ideal protocol has the following order.

1. Prepare a separate full Q auxiliary A in uniform logical +, and M in
   uniform logical 0, using their respective CSS checks. Initialize the data
   canonical register in uniform logical 0 for GHZ preparation.
2. Apply **A control -> M target**, with the 9,075 disjoint coordinate pairs.
   Destructively measure M in Z. This measures the entire embedded Z logical
   algebra of M on A. Retain all allowed outcomes.
3. Correct or track the resulting Pauli-X sign frame on A. The ideal corrected
   A is a uniform logical + state of the effective CSS code defined below.
4. Apply **A control -> data target**, the 9,600-pair identity matching.
   Destructively measure A in X and decode the desired 300 parities and the
   additional two residual parities. If the mask X frame was tracked, propagate
   it to the data; it is not removed by the X readout.
5. Apply the previously approved physical automorphism. Canonical inputs are
   |000+> in the corrected frame, yielding GHZ4. Transform the Pauli frame
   through the automorphism and retain the final GHZ sign correction.

PROVED: this construction does not assume the desired mixed logical mask is
already available. Only uniform logical +/0 states of Q and M are input
resources. Their fault-tolerant preparation remains a separate obligation.
The effective additional Z checks below are NOT directly measured as large
check operators: the M protocol implements their logical projection.

FALSIFIED: the same punctured M used with the CNOT direction reversed is not
a homomorphic X-measurement helper. The two inclusion-failure counts are
2,625 and 225. The two-stage mask, rather than this wrong-direction shortcut,
is the load-bearing change from the previous proposal.

## Complete measured algebra, including residuals

PROVED: in binary row-support notation,

`HX_M = HX_Q restricted to S`,

and zero-extension embeds `HZ_M` into `row(HZ_Q)`. These verify both
code-preserving inclusions for Q-controlled CNOT into M. They hold for the
actual binary lifts; no field rank or HGP distance formula is substituted.

The Z observables measured in stage 2 span

`L = iota ker(HX_M)` modulo `row(HZ_Q)`.

The entire space, not just selected representatives, is certified by:

| Binary quantity | Value |
|---|---:|
| dim ker(HX_M) | 3,849 |
| rank(HZ_Q restricted to R) | 223 |
| dim Z stabilizers of Q supported on S | 3,134 - 223 = 2,911 |
| rank(HZ_M) | 2,911 |
| independent measured Zs | 3,849 - 2,911 = 938 |

NUMERICAL: all 900 unwanted canonical Zs have zero support on R, are
normalizers, and are independent modulo data Z stabilizers. All desired
canonical Xs are supported on R, so commute with every element of L. Thus
the measured algebra is 900 unwanted canonical Z directions plus 38
canonical-central residual Z directions. Residual modes are not discarded
from the dimension count and are not assumed to be harmless without checking.

The effective auxiliary code is defined algebraically by

`HX_eff = HX_Q`, `row(HZ_eff) = row(HZ_Q) + L`.

Its logical count is `1240 - 938 = 302`. The 300 selected canonical Xs and
two residual Xs from the prior raw helper are independent modulo HX_Q,
are data normalizers, and are supported on R. They therefore belong to the
final measured space and, by the dimension equality, span all of it.
The two residual Xs commute with ALL 1,200 canonical Z generators.

PROVED: arbitrary residual information is not preserved. The main factory
contract permits residual fixing/measurement because it is outside the
canonical GHZ register. Strictly 300 measurements with no residual readout
remain OPEN: changing only the existing mask's measurement basis cannot
remove the two residual Xs supported on the disjoint strip R. A different
interface or additional mask is needed.

## Distance and signed-channel certificates

NUMERICAL: all binary syndrome columns in HX and HZ of both Q and M are
nonzero and pairwise different. Thus every pure X/Z weight-one/two error has
nonzero syndrome. The independent audit also handles degenerate examples by
testing stabilizer cosets; it is not merely a duplicate-column heuristic.
For a CSS code, a nontrivial mixed logical operator has a nontrivial pure
component of no greater weight, so the same lower bound excludes mixed
logical errors of these weights.

PROVED: `d_X_eff >= d_X_Q` and `d_Z_eff >= d_Z_Q`: adding commuting logical
Z stabilizers shrinks X normalizers and enlarges Z stabilizers, without
changing HX. Hence the effective auxiliary also has both distances at least
three. Zero-extension is weight-preserving and injective on M's Z homology,
so `d_Z_M >= d_Z_Q`. The analogous data-relative X-distance bound for M is
OPEN; only its independent finite lower bound is claimed.

NUMERICAL: an independent four-logical-qubit channel audit checks all
8 mask outcomes times 16 final X outcomes. With m on the three unwanted
coordinates and b on all four, its raw data Kraus operator is

`K_(m,b) = (-1)^(m dot b) X^m [I + (-1)^b4 X4] / 16`.

After the known mask X frame is removed, this is a scalar multiple of the
X4 projector and identity on the other three data coordinates. This checks
arbitrary coherent input, not only a basis-state GHZ example. All 128
branches on |0000> have probability 1/128 and produce GHZ after the proper
frame/automorphism. Dropping the propagated mask frame gives average GHZ
fidelity 1/8; reversing the mask CNOT is also a negative control.
No logical-outcome postselection is used.

## Structural resource comparison

NUMERICAL; all qubits below are code carriers, excluding syndrome ancillas,
verification resources, routing, buffers, spares and classical hardware.

| Quantity | Previous raw helper | Two-stage protected candidate |
|---|---:|---:|
| auxiliary carriers during preparation | 525 | 9,600 + 9,075 = 18,675 |
| online data + final auxiliary | 10,125 | 19,200 |
| resident data + full preparation peak | 10,125 | 28,275 |
| interface CNOT count | 525 | 9,075 + 9,600 = 18,675 |
| ordered matching layers, excluding all other service | 1 | 2 |
| final canonical / residual X measurements | 300 / 2 | 300 / 2 |
| auxiliary Z distance evidence | exactly 1 | at least 3 |

The 28,275 figure assumes the data remains resident during mask preparation;
it is not an unavoidable peak if preparation is offline and M is freed
before the data is loaded. The two matchings cannot collapse into one stage:
mask readout and frame determination intervene. Matching depth assumes free
connectivity and does not include array motion or the final automorphism.

| Native supplied check structure | Q / full auxiliary | M |
|---|---:|---:|
| X checks / rank | 5,250 / 5,226 | 5,250 / 5,226 |
| Z checks / rank | 3,150 / 3,134 | 2,925 / 2,911 |
| X maximum row weight / edges | 10 / 45,150 | 10 / 42,525 |
| Z maximum row weight / edges | 13 / 34,650 | 13 / 31,950 |
| maximum column degree, each type | 7 | 7 |

The auxiliary pair has 16,575 supplied checks; one syndrome qubit per check
would be only a circuit-design convention, not a verified FT-space estimate.
No rounds or seconds are substituted for the two structural CNOT layers.

## Source domain, reproducibility and review

LITERATURE: [Xu et al., v1, Section V.1 / Algorithm 2](https://arxiv.org/html/2407.18490v1#S5.SS1)
motivates the two-stage mask. Its Section IV.4.2 HGP distance argument has
full-rank/classical-product hypotheses and is not adopted as an LP theorem.
The finite LP binary matrices and residual sector are audited here instead.
The RASCqL comparison and private completed-seed transcription are inherited
from the approved prior task, not newly re-audited source claims.

Generate with `.venv/Scripts/python.exe scripts/run_lp_protected_ghz_cycle.py`.
Outputs: `experiments/runs/T-20261001-004/summary.json` and
`reproducibility.json`; generated outputs must not be edited by hand.
The manifest pins unchanged constructor and literature hashes; provenance
records dirty-tree content hashes, Python/numpy, commit, output and no seed.

Review priority: the CNOT direction; complete-space rank argument; signed
outcome correction; the distinction between finite distance and circuit FT;
and the conditional space accounting. Small explicit-kernel tests and a
separate full-size kernel spot audit support the efficient rank certificate.
Repeat a full-size kernel rebuild only if a specific gap remains. Current
validation commands and counts are in the session and review records.
