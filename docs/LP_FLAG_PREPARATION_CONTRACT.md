# Two-pass flagged uniform LP preparation

- Task: T-20261001-008; owner: codex; status: IN_REVIEW.
- Review: RV-20261001-008, PENDING with claude.
- Baseline: HEAD103e62e; input E-20261001-008; no production random seed.
- Scope: prepare uniform logical plus on Q and uniform logical zero on M.
  The matrices, direct GHZ mask, logical outcome map and automorphism inherited
  from approved tasks are unchanged. This is NOT an arbitrary-data decoder or
  a complete GHZ-factory FT certificate.

## Fixed circuit and actual acceptance

CHECK: Q starts in physical plus and measures HZ_Q; M starts in physical zero
and measures HX_M. Each supplied check uses a syndrome ancilla s and flag f.
For a Z check, prepare s in zero and f in plus, apply f->s, all data->s CNOTs
in ascending support order, then f->s; measure s in Z and f in X. For X checks,
use the global-H dual: s in plus, f in zero, s->f, s->data, s->f, read s in X
and f in Z. This duality is a description, not additional physical H gates.

Run two COMPLETE passes with no correction between passes. Accept iff every
flag is zero, the full raw syndrome vectors agree, and that common vector is
in the check matrix's syndrome image. Track an exact preparation Pauli frame
only after acceptance. In the noiseless case every valid random projection
outcome is accepted, not only the all-zero syndrome. No selection is performed
on the later 938 logical mask-result bits.

LITERATURE: Chamberland and Beverland, arXiv:1708.02246v3, section3.3 and
Figure11(a), give a general one-flag measurement with two flag CNOTs. Their
full FTEC construction additionally has conditions on distinguishability.
Source: https://arxiv.org/html/1708.02246v3#S3.SS3 (read 2026-10-01).
Our all-data bracketing placement is an explicitly specified variant; it is
not claimed to be a literal Figure11(a) transcription or an application of
that paper's complete FTEC theorem to LP. Its local and global properties are
proved below and separately checked. No extra cat resource is used for these
check gadgets; the later intended OUTPUT is still a GHZ resource state.

## Conditional single-fault statement

PROVED for the specified circuit and single-Pauli model, pending cross-review:
each declared single fault is either rejected by the implemented records or,
after interpreting the same record-dependent preparation frame, leaves the
uniform target state with an error equivalent to a Pauli of weight at most1.
The equivalence is modulo the complete TARGET-STATE stabilizers, not just the
code stabilizers and not an unobserved opposite-axis syndrome.

Here is the branch-independent argument in the Z-check convention. Let H be
the measured binary matrix. The pure target has Z group row(H) and X group
ker(H), altogether n independent stabilizers. Write E=X(x)Z(z) for the
propagated error and delta_1,delta_2 for the two actual record shifts from an
arbitrary valid ideal branch m. Acceptance requires zero flags, equal shifts
delta and m+delta in im(H). Any exact correction C with H C(y)=y has

    H [x + C(m) + C(m+delta)] = H x + delta.

Thus the corrected residual is fully characterized by

    (H x + delta, z modulo row(H)).

The map need not be a low-weight noisy decoder. A large X representative
with zero H signature is a stabilizer of this UNIFORM plus target. This is
not true of an arbitrary unknown logical input and must not be generalized.

For an unflagged local fault, the data error is one-site, zero, or a complete
measured Z check. A spreading syndrome-Z in the interior produces a flag.
The apparently dangerous correlated Z_f Z_s fault after the opening flag
CNOT can cancel its flag, but then produces the FULL measured check, harmless
in row(H), rather than an interior suffix. Closing-flag faults touch no later
data. Data X only propagates into readout records, not other data sites.

If the fault is in pass1, the clean pass2 yields delta=H x, so the entire X
part is removed modulo ker(H) and the unflagged Z part has weight<=1 modulo
row(H). If in pass2, clean pass1 forces delta=0; the remaining unflagged
data Pauli already occupies at most one site modulo a full check. Initial
preparation, intervening/final in-scope idles, resets and readout flips obey
the same argument. Checks may overlap; their same-axis couplings do not
transmit data errors into other data. M follows by global-H duality.

## Exact finite-instance evidence

NUMERICAL: the primary circuit has64 concurrent check/flag pairs per block.
The audit propagates Pauli maps BACKWARD to actual records and the full target
quotient. It compares every accepted residual to the complete set of identity
and all3n single-Pauli target signatures. It neither truncates support nor
uses a sampled set of ideal outcomes. The two ideal sign spaces have ranks
3134 and5226, covering 2^3134 and2^5226 preparation outcomes respectively.
The inherited exact sign-recovery maps are freshly checked independently.

Coverage: all15 nonidentity post-CNOT Paulis; all3 post-preparation/reset
Paulis; one classical outcome flip per readout (pre-readout Paulis reduce to
this or an irrelevant phase); all3 Paulis on each live idle location. Reset
is part of fresh ancilla preparation, not an extra uncharged operation.
Inactive pool qubits are reset before reuse and have no live quantum state.

| Primary cap64 | Q plus | M zero |
|---|---:|---:|
| Data carriers | 9,600 | 9,075 |
| Supplied checks | 3,150 | 5,250 |
| Two-pass CNOTs | 81,900 | 106,050 |
| Abstract ticks including initial prep | 1,571 | 2,131 |
| Live idle locations | 15,080,760 | 19,345,810 |
| Enumerated single-Pauli fault cases, with multiplicity | 46,549,980 | 59,739,405 |
| Accepted: exact target modulo its stabilizers | 3,221,156 | 2,888,393 |
| Accepted: minimum target-coset weight1 | 24,708,568 | 29,091,954 |
| Rejected | 18,620,256 | 27,759,058 |
| Accepted with no weight<=1 representative | 0 | 0 |

The106,289,385 fault cases are NOT independent noisy shots and do not define
a physical failure probability. Idle Pauli maps are unchanged between two
consecutive operations on the same live wire, so identical maps are evaluated
once with their exact time multiplicity. There are3,593,790 evaluated map
cases before multiplying idle multiplicities. Actual output syndrome/flag
effects and the corrected state class are identical throughout each group.

NUMERICAL: the old Q row0/third-data-CNOT syndrome-Z hook now flips actual
flag0 and is rejected. The corresponding M witness is also flagged. No
terminal ideal Q-X record is assumed. This addresses the former obstruction
by adding a physically measured record, not by changing the recovery oracle.

Independent checks use different representations and directions:

- A dense six-qubit statevector/projector verifier, importing neither the
  construction nor the analysis, checks all4 valid branches of overlapping,
  dependent checks and828 specified fault events per axis. Each axis has992
  accepted faulty branches, none outside the target's single-Pauli orbit;
  max infidelity is below7e-16. Dropping flags or omitting repetition produces
  an accepted bad state with zero overlap with that entire orbit.
- A second tiny-circuit oracle explicitly lists every live wire on every
  tick, propagates physical faults FORWARD and brute-enumerates target
  stabilizers and corrections. All per-kind histograms match the backward
  audit for six schedules, covering both axes, overlap, dependencies and
  partially occupied batches. This checks the omitted dense-replay timing
  windows and the exact idle compression.

## Structural resources and time boundary

CHECK: connectivity is unrestricted; native routing is not synthesized. Each
batch has pair preparation, opening flag CNOT, greedy data-CNOT layers,
closing flag CNOT, then simultaneous syndrome/flag measurement. Short rows
remain live to the common batch measurement. All data remain live to that
block's final ancilla measurement. Q/M have separate pools.

NUMERICAL: preparation costs187,950 CNOTs and18,931 concurrent qubits at
cap64, including18,675 carriers and256 ancillas. The old77,175 count was one
bare preparation pass, not an FT alternative of equal guarantee. The9075
downstream matching CNOTs are NOT included or certified in this cycle.

| Check/flag pair cap per block | Q ticks | M ticks | Total qubit peak | Q+M live idle locations |
|---|---:|---:|---:|---:|
| 1 | 94,501 | 127,051 | 18,679 | 2,060,178,750 |
| 64 | 1,571 | 2,131 | 18,931 | 34,426,570 |
| 256 | 443 | 623 | 19,699 | 9,971,870 |
| All checks | 53 | 47 | 35,475 | 1,284,150 |

The nonprimary caps are structural sensitivities, not additional full-instance
fault censuses or optimal schedules. These ticks are NOT QEC cycles/seconds.
For B batches and D data-CNOT layers PER PASS, symbolic attempt duration is

    t_init + 2 B (t_pairprep + 2 t_flagCNOT + t_pairread)
           + 2 D t_dataCNOT + t_classical_accept_and_frame.

Pair preparation/readout times mean the parallel service of the two bases,
not two serial measurements. The fault time grid declares one idle location
per abstract layer; changing physical durations requires a compatible idle
noise model, not a silent reinterpretation of these counts.

OPEN: the certificate ends at the final quantum measurement, with an ideal
interpreted frame. Classical processing latency and its storage faults,
physical correction gates, leakage/crosstalk, routing and multi-fault events
are not covered. With equal abstract tick durations and synchronous starts,
Q must additionally wait560 ticks for M, exposing5,376,000 data-idle sites;
those lie OUTSIDE this preparation certificate. Random separate retries
introduce further waiting and need a buffer/QEC policy.

## Rejection and retry diagnostic

NUMERICAL: the artifact gives exact first-order rejection coefficients for
each primitive class. With uniform nonidentity Pauli noise conditional on
each fault, P(reject)=sum c_kind p_kind+O(p^2), at FIXED circuit size. If all
location probabilities were equal, the coefficients sum to5,926,352 for Q
and26,675,938/3 for M. This expansion must NOT be used as a finite-p yield
estimate when number_of_locations times p is large.

PROVED under explicitly CHECK independent classical readout flips at rate
p_m<=1/2, independent of other faults: for R checks on ONE block,

    P_accept <= (1-p_m)^(2R) [(1-p_m)^2+p_m^2]^R.

Condition on any true readout pattern. Each flag is reported zero with
probability at most1-p_m. Each disjoint syndrome-readout pair agrees with
probability at most(1-p_m)^2+p_m^2. Further dependent-check consistency only
reduces acceptance. This bound does not assume the quantum circuit is ideal,
but DOES require the stated independent, nonadaptive readout-flip model.

| Assumed p_m | Q acceptance upper bound | M acceptance upper bound |
|---|---:|---:|
| 1e-4 | 0.2836450921 | 0.1224499999 |
| 1e-3 | 3.361417173e-6 | 7.542882760e-10 |

CHECK: whole-block rejection is therefore a useful safety reference, not a
demonstrated practical high-throughput factory. These are UPPER BOUNDS, not
yield estimates or logical failure rates. For independent identical retries
of each block, expected attempts are1/P_accept separately; do not multiply
Q/M probabilities unless both restart together. Finite-noise accepted yield,
waiting, buffer memory, decoder cost and service throughput remain OPEN.

## Reproduction and review boundary

Run `.venv/Scripts/python.exe scripts/run_lp_flag_preparation_cycle.py`.
The default local/ignored output is `experiments/runs/T-20261001-008/`;
`--output` supports a separate fresh regeneration. Summary is deterministic;
provenance additionally records full HEAD, dirty-tree status, direct source
and input hashes, Python/numpy/platform, output path and validation scope.
Never hand-edit generated files. See the session for actual test commands,
summary digest and comparisons.

Review the new circuit ordering, complete target-state quotient, branch
argument, fault-location accounting and retry interpretation. Approved LP
matrices/distances/private-source transcription are inherited unchanged;
repeating those earlier studies is not required absent a concrete concern.
Noisy matching/mask decoding, automorphism and a complete GHZ factory remain
OPEN. Do not relabel this preparation-only statement as full-factory FT.
