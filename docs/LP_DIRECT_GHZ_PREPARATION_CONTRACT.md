# Direct retained-block LP GHZ preparation

- Task: T-20261001-006; owner: codex; status: DONE.
- Review: RV-20261001-006, APPROVED by claude on 2026-10-01; no required changes.
- Input: E-20261001-006; starting HEAD bd32ab9a329a00edbb87e831edd234668eed8ac2.
- Scope: one completed LP instance, 300 canonical GHZ4 outputs; no arithmetic
  runtime or T/i-state factory. This is resource-state preparation, NOT an
  arbitrary-data PPM instrument.

## Direct protocol and admission boundary

PROVED, conditional on the verified finite binary identities and ideal inputs:
the approved T-20261001-004 mask prepares a full Q auxiliary whose
canonical sector, after correcting its known X frame, is 300 copies of
|000+>. Retain this block as the output and apply the approved physical
automorphism directly. The next data block, the second 9,600-CNOT matching,
and destructive X readout of the retained block are unnecessary for this
specialized state-preparation task. The all-outcome certificate is implemented
and tested in this cycle. The arbitrary-input measurement interface from the
previous task remains a distinct, unchanged result.

1. Prepare Q in uniform logical plus and M in uniform logical zero.
2. Apply Q control -> M target on the 9,075 injected coordinate pairs.
3. Z-read M, retaining every allowed outcome; decode a known Pauli X frame.
4. Physically correct that frame before the automorphism, or conjugate and
   retain the output frame. Do not silently drop or leave it untransformed.
5. Retain the 9,600-qubit Q output. No final destructive X measurement.

NUMERICAL: the mask fixes 900 canonical Z and 38 residual Z modes. The surviving
logical X stabilizers are 300 selected canonical X and two residual X modes.
The residual sector is freshly prepared, not an unknown state to preserve.
The code has 40 residual logical modes, explicitly retained in the accounting.

## Required ideal certificate

NUMERICAL: full-instance results are generated from exact GF(2) rows,
including an explicit 938-bit outcome map, its physical X-frame duals,
canonical/residual separation, and all 1,200 target GHZ stabilizers. There are
2^938 logical outcome branches, not 938 branches. Generator-level identities
cover the entire space. Allowed physical M readouts additionally have
5,226 stabilizer-randomness degrees of freedom; these cannot alter the decoded
logical signs. No logical-outcome postselection is allowed.

A construction-independent ten-logical-qubit dense replay checks one quartet,
one fixed residual Z and one retained residual X over every one of its sixteen
branches. This checks signed reduced semantics, not the full physical LP code.

PROVED: write L for the 938 measured Z rows and D for their 938 physical
X-normalizer duals. The checked identity L D^T=I implies that X(D^T m)
corrects every outcome vector m. All retained X stabilizers commute with this
correction. Thus all corrected pure states coincide, not just sampled branches.
The 9,075-bit valid readout space ker(HZ_M) has dimension 6,164. Its quotient
by row(HX_M), dimension 5,226, is exactly the 938-dimensional outcome space:
the decoder kills HX_M and the restricted duals give a right inverse. These
are ideal linear sign maps, NOT a noisy-readout decoder.

For each quartet, raw input is |m0,m1,m2,+>. The computational g^T maps this
to X0^(m0 xor m1 xor m2) X1^m1 X2^m2 GHZ4. All XXXX signs are positive;
ZZ(0,3), ZZ(1,3), ZZ(2,3) signs are respectively m0 xor m1 xor m2, m1, m2.
Residual-only outcomes do not enter these signs. Physical dual representatives
have weights 102..2,220, but these are NOT a required number of physical gates:
the primary protocol tracks the known frame and conjugates it through the
automorphism. Frame processing and later interpretation are still obligations.

NUMERICAL: all 1,200 canonical output stabilizers and residual centralizers
pass. Dense replay residual is zero, with sixteen branches of probability
1/16. Omitting the canonical mask frame gives mean quartet GHZ fidelity 1/8;
using an untransformed output frame gives 1/2; wrong auto orientation gives
1/4. On the full ideal uniform ensemble, omitting the frame leaves the correct
canonical signs only in fraction 2^-900; this is not a physical failure rate.

## Explicit preparation baseline and costs

CHECK: use one cat-free bare-check projection pass, not an FT preparation:
Q starts physical plus and measures its supplied Z checks; M starts physical
zero and measures its supplied X checks. Check order and support order are
deterministic. Concurrent check-ancilla caps are sensitivity parameters, not
hardware connectivity guarantees. Preparation syndrome signs are distinct
from mask logical outcomes and require their own Pauli-frame record.

NUMERICAL: independent linear right inverses handle all allowed initial
projection syndromes: 3,134 Q-Z sign bits and 5,226 M-X sign bits. The primary
baseline applies ideal physical X_Q and Z_M corrections before matching,
requiring a symbolic parallel single-qubit layer and classical processing.
This particular right inverse uses at most 8,360 correction sites in total;
the generic resource report conservatively bounds by all 18,675 carriers.
X_Q preserves the uniform logical-X plus state; Z_M preserves uniform logical
Z zero. If tracked instead, X_Q also flips M's readout and Z_M propagates onto
Q through the matching. Neither may be silently dropped. Correction-gate
noise is excluded from the bounded census, not assumed physically absent.

Structural expected counts: Q 3,150 checks / 34,650 check CNOTs; M 5,250 checks /
42,525 check CNOTs. Combined preparation 77,175 CNOTs plus 9,075 interface
CNOTs = 86,250, excluding physical frame gates and the automorphism.
These are single-projection-pass counts, not a certified number of FT rounds.
Q+M requires 18,675 code carriers; add peak concurrently live syndrome ancillas.
Mask readout frees M; output Q remains allocated. Routing, verification,
repeated extraction, buffers/spares and decoder hardware are not included.

CHECK: the prior 28,275 peak assumes the data block remains resident throughout
preparation. Prior offline preparation can instead peak at 19,200 for data+A;
do not claim an unconditional 9,600-qubit reduction against that schedule.
One matching stage is not one QEC cycle. Native time/failure fields stay null.

NUMERICAL: deterministic ascending-support, row-batched greedy schedules:

| Requested syndrome ancilla cap per block | Actual total syndrome ancillas | Bare baseline peak qubits | Q batches / CNOT layers | M batches / CNOT layers |
|---|---:|---:|---:|---:|
| 1 | 2 | 18,677 | 3,150 / 34,650 | 5,250 / 42,525 |
| 64 (primary) | 128 | 18,803 | 50 / 585 | 83 / 733 |
| 256 | 512 | 19,187 | 13 / 169 | 21 / 227 |
| 5,250 | 8,400 | 27,075 | 1 / 22 | 1 / 19 |

The two blocks prepare concurrently using separate pools. Each batch includes
ancilla reset/preparation and measurement; total preparation time is the max
of the two block durations, not the sum. CNOT layers alone omit these costs.
These schedules are reproducible heuristic schedules under unrestricted
coupling, not optimal depth bounds or QEC rounds. The complete symbolic time is

`max(T_Qprep,T_Mprep) + T_prep_sign_processing + T_parallel_prep_Paulis
 + T_matching + T_mask_Z_readout + T_mask_frame_processing + T_automorphism`.

Mask and syndrome pools can be released before subsequent output storage.

## Bounded fault diagnostic

CHECK: enumerate the spreading-axis ancilla fault immediately after every
supplied check CNOT: Z on Q's Z-check target ancilla and X on M's X-check
control ancilla. Also inspect individual M Z-readout bit flips. Propagate
through the remaining same-axis checks and Q->M matching where relevant.
Declare coverage, known records and excluded locations explicitly. This is
not all 15 two-qubit Pauli faults or a full circuit-noise simulation.

OPEN: a bare hook's high weight or nonzero ideal terminal syndrome is not
proof of logical failure or correctability. Terminal perfect syndrome is
diagnostic only unless explicitly implemented. To claim correction, all
fault candidates consistent with the actually available record must admit
a common recovery into the declared allowed residual-error set. No such
full FT admission follows from this initial census. Flags, a noisy decoder,
repetition counts, idle errors and Monte Carlo remain future tasks.

NUMERICAL: census covers 34,650 Q-Z hooks, 42,525 M-X hooks and 9,075 M-readout
bit flips: 86,250 specified fault events (not a complete circuit fault set).
31,500 Q hooks have nonzero hypothetical terminal HX syndrome, but no such
syndrome is collected in this baseline. 37,275 M hooks have nonzero actual
HZ_M parity from the final Z-readout. All 9,075 single-bit readout flips have
nonzero, distinct HZ_M columns. Raw canonical mask parity corruption spans
0..118 for a single readout flip. None of these counts is a decoded failure rate.

### Concrete failure of the bare common-recovery criterion

FALSIFIED: without an additional record, this bare baseline cannot have one
record-conditioned Pauli recovery that leaves BOTH no-fault and every covered
single-fault output equivalent to at most one physical error. Equivalence
allows code stabilizers, canonical target-state stabilizers and arbitrary
residual logical Paulis. This is a declared finite criterion, not every
possible FT definition or an impossibility theorem for LP GHZ factories.

Q Z-check row 0 has ascending support
`[0,79,152,232,342,400,478,7350,7613,7873]`.
A Z on its check ancilla immediately after the third CNOT produces output Z
support `[232,342,400,478,7350,7613,7873]`. Multiplying by that check yields
the weight-three representative `[0,79,152]`.

Against HX_Q plus the 300 retained canonical Xs, its nonzero signature rows
are `[0,79,152,563,642,715,1123,1127,1200]`. An exhaustive complement lookup
excludes zero, all 9,600 single columns and all 46,075,200 unordered column
pairs. Consequently the minimum weight modulo the harmless group is exactly
three. Mixed Paulis cannot evade this test: their signature against pure-X
constraints depends only on their Z component of no greater weight.

PROVED, conditional on these exact signatures: the fault has the same entire
classical record as no fault, branch by branch. Its ancilla Z gives only a
phase at Z-readout; its data Z commutes with later Q-Z projections, the
control-side matching and all M-Z readouts. Conditional Pauli corrections
change only a global phase. If a common recovery left each history within
weight one, their difference would have a representative of weight at most
two, contradicting the signature exclusion. The physical automorphism is a
permutation, so preserves this obstruction. This witness does not require an
incorrect GHZ sign before QEC; code-space errors alone matter to the criterion.

OPEN: extra Q-X extraction or flags can distinguish these two histories, but
must themselves be audited with noisy records and a recovery rule. A perfect
terminal syndrome is diagnostic evidence, not a completed fix.

## Reproducibility and review

Inherited constructor/canonical convention and mask artifacts are hash-pinned
in the manifest, with approved dependency reviews. Do not reopen private PDF
transcription absent a concrete discrepancy; no new literature theorem is
claimed. Generated artifacts must be regenerated from the source and manifest.
Review covered the direct specialization, signed outcome map, residual
factorization, resource lifetimes and precise fault-coverage boundary; see
the review record for inherited versus independently reproduced evidence.

Generate with `.venv/Scripts/python.exe scripts/run_lp_direct_ghz_cycle.py`.
Outputs are `experiments/runs/T-20261001-006/summary.json` and
`reproducibility.json`. The latter records dirty-tree content hashes, input
manifest, environment, commit, output path, null random seed and review state.
Validation commands/counts and regeneration hash are recorded in the session.
Cross-review is APPROVED; task DONE, D-0038 ACCEPTED and lock RELEASED.
Approved predecessor results and generated submission artifacts are unchanged.
The generated PENDING field is historical; the review queue is authoritative.
Reviewer scope limits are preserved: individual physical X-dual weights and
dense negative-control fidelities were not separately recomputed, and the
unchanged private-PDF seed transcription was not reopened. No FT factory,
noisy decoder or native runtime/failure claim is newly admitted by approval.
