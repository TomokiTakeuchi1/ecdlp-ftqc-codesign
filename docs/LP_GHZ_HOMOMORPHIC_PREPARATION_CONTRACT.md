# Completed-LP fixed-mask GHZ preparation

- Task: T-20261001-001
- Owner: codex
- Status: DONE; RV-20261001-001 APPROVED by claude, 2026-10-01; lock RELEASED

Review scope: no required changes. Claude independently checked the finite
algebra, canonical pairing, conditional g-to-g^T orientation argument and
single-Z fault witness. Private-PDF transcription and the literal 9,600-qubit
physical permutation were not independently reverified by the reviewer.
Approval does not admit either helper as an FT factory. See
coordination/reviews/T-20261001-001.md for the full scope and limitations.

## Scope

The human selected ripple-carry resource preparation rather than QCLA profiling.
This cycle targets Q_one from the September 30 attachment: a 9,600-data-qubit
completed LP candidate with 1,200 canonical logical qubits in 300 quartets and
40 residual logical qubits. The dimension and basis claims are reproduced below;
the source's distance claims are not re-certified here.

The original proposed family X_(1,j,a) is a negative control, not silently
retained. The binary convention audit below corrects it to X_(4,j,a), for four
values of j and 75 lift positions a. A single product of all 300 Xs is NOT
sufficient.

## Acceptance and evidence boundary

1. Reproduce CSS commutation, ranks and the relevant canonical pairing/action.
2. Give explicit auxiliary checks and a physical coupling map, or an exact
   obstruction to a precisely delimited candidate (not an LP impossibility claim).
3. Check the full induced measurement space, including unwanted logical
   information and residual-sector effects, not just selected observables.
4. Account for auxiliary initialization without assuming the same unavailable
   mixed-state primitive. Keep circuit-level FT certification separate.
5. Report structural qubits, coupling count/depth and concurrency constraints;
   leave unsupported syndrome rounds, failure probability and seconds OPEN/null.
6. Independent tests/replay and Claude cross-review submission.

Homomorphic CNOT is the primary route. Surgery is a documented fallback, not a
second full implementation this cycle. T/i preparation, consumption, full
arithmetic mapping and large Monte Carlo are out of scope.

## Outcome

- NUMERICAL: exact binary reconstruction reproduces the finite 9,600-qubit
  instance and all 1,200 paired canonical logical generators.
- PROVED: with the attachment's X-check/Z-homology convention, the physical
  automorphism acts by g on Z labels and by g^T on computational bits. Its
  GHZ input is |000+>, not |+000>. Relabeling the logical basis can change the
  name of the input, but that change must be explicit.
- NUMERICAL: a 525-qubit helper and 525 matching CNOTs implement 302 logical X
  measurements, consisting of the desired 300 plus two residual observables.
  Two additional weight-75 Z checks produce a strict 300-only helper.
- FALSIFIED: either helper, used once with the specified unprotected readout,
  is a fault-tolerant GHZ factory. Both have d_Z=1 and an explicit single-fault
  wrong-GHZ-sign witness. This is NOT a no-go theorem for LP homomorphic
  measurements, repeated measurement, or larger protected helpers.
- OPEN: protected auxiliary construction, preparation/extraction circuit
  distance, decoding, native timing, full factory footprint and failure rate.

## Source and convention pin

The input attachment is Application-Tailored Automorphisms in Lifted-Product
Codes: Two-Copy Equivariant Completion and a Concrete AutoCNOT Candidate,
September 30, 2026, 32 pages, local filename
RASCqL_with_lifted_product_codes2.pdf. SHA-256:
b498151c8d6d011ad559682d21e6364324be60c7886eecacbdf99118696f5cc1.
Pages 10, 14 and 23 were visually inspected, in addition to full relevant
text extraction. The private PDF is not redistributed. Its exact seed input
is transcribed in E-20261001-001.json.

LITERATURE: [RASCqL v2, Fig. 7 and Appendix C.3](https://arxiv.org/html/2602.14273v2)
uses uniform-eigenstate patches, puncturing and homomorphic measurements for
mixed initialization, followed by autoCNOT entangling. This does not certify
the completed LP seed. LITERATURE:
[canonical LP, Section V.1](https://arxiv.org/html/2607.28605v1) supplies the
surgery fallback, whose finite-instance conditions remain to be checked.
The local public PDFs and versions are hash-pinned in the manifest.

All support vectors below are binary columns. The ring is
R=F_2[x]/(x^75+1), and x^t binarizes with a 1 at row c, column c-t modulo 75.
The checks are H_X=B(d1), H_Z=B(d2*) as in the attachment.
Thus ker(H_X)/row(H_Z) describes Z logicals, not X logicals.
We construct actual binary normalizers rather than rely on the attachment's
ambiguous ring-involution notation for logical representatives.

## 1. Reconstructed instance and canonical section

The 3-by-7 seed exponents are

    0  71  73  68  33  50  47
   38  39  60  26  18   1  23
   73   6   5  42  20  22  73

The information columns are J=(3,4,6,7), one-based. The completion is

\[
 \widetilde A=
 \begin{pmatrix}A&0\\0&A\\Wg\pi_J&W\pi_J\end{pmatrix},\quad
 g=\begin{pmatrix}1&0&0&0\\1&1&0&0\\1&0&1&0\\1&1&1&1\end{pmatrix},
\quad W=\begin{pmatrix}0&0&1&0\\1&0&1&0\\0&0&1&1\\0&1&0&1\end{pmatrix}.
\]

NUMERICAL: exact GF(2) checks, not floating-point rank estimates:

| Matrix | Binary shape | Rank | Check incidences |
|---|---:|---:|---:|
| A | 225 x 525 | 223 | 1,575 |
| tilde A | 750 x 1,050 | 746 | 4,200 |
| H_X | 5,250 x 9,600 | 5,226 | 45,150 |
| H_Z | 3,150 x 9,600 | 3,134 | 34,650 |

The full H_X H_Z^T is zero; k=9,600-5,226-3,134=1,240.
Maximum X/Z check weights are 10/13. No data-code distance is inferred from
these ranks, and this cycle does not reproduce the attachment's distance search.

The non-free base kernel requires an explicit canonical section E. Choose
pi_J E=I and zero parity on base coordinate fibres 2 and 5. This removes the
two trivial-character ambiguities. The four generating binary words have
weights 102,108,126,114; cyclic shifts produce the 300-dimensional canonical
subspace. Their full hexadecimal supports are in summary.json.

NUMERICAL: constructed X/Z normalizers have identity symplectic pairing on all
1,200 generators. The remaining 40 logical qubits are the symplectic complement;
we do not assume they are absent or unencoded.

## 2. Correct automorphism orientation

The physical permutation swaps the two seven-coordinate blocks of tilde A,
and swaps check rows (1,4),(2,5),(3,6),(7,8),(9,10), one-based.
It preserves each supplied X/Z check set exactly.

Let z_i=(E e_i,E g e_i) tensor f_j denote a canonical Z support.
PROVED: the swap sends z_i to the g-column combination of the z_k. The
paired X action is inverse transpose. Since g^2=I,

\[
 U Z(v)U^\dagger=Z(gv),\qquad
 U X(w)U^\dagger=X(g^T w),\qquad U|u\rangle=|g^T u\rangle.
\]

NUMERICAL: all 1,200 X and 1,200 Z generator identities pass modulo the
appropriate stabilizers. Using the opposite X orientation fails all 1,200
X-generator checks. An independent dense implementation also verifies all
eight single-quartet Pauli conjugations.

Consequently:

\[
 U|000+_m\rangle=
 (|0000\rangle+(-1)^m|1111\rangle)/\sqrt2,\qquad
 U|+000\rangle=|+000\rangle.
\]

The source's Eq. (104)/(115) is not consistent with its stated convention
without a logical-basis redefinition. We keep the original physical code and
change the selected logical row to i=4 (physical first-copy coordinate p=7).
A Z on any one GHZ member corrects the sign; the verifier uses member 4.
Both outcomes are accepted. No outcome-sign postselection is needed.

The canonical symplectic subspace is invariant, so the automorphism also
preserves its residual symplectic complement. It need not act as identity on
those 40 residual logicals.

## 3. Explicit homomorphic coupling

Let C be a 525-by-9,600 injection matrix from helper controls to data targets.
Helper coordinate (k,a) couples to data coordinate (p=7,k,a) in the first
qubit summand of Q_one. Zero-based target indices are 3150 through 3674.
This is 525 disjoint pairs, hence one CNOT matching layer if connectivity
permits. It is not a hardware routing or cycle-time guarantee.

For row-vector support bookkeeping, code-space preservation requires

\[
 \operatorname{row}(H_X^a C)\subseteq\operatorname{row}(H_X^d),\qquad
 \operatorname{row}(H_Z^d C^T)\subseteq\operatorname{row}(H_Z^a).
\]

NUMERICAL: both inclusions pass for both helpers below. The first is vacuous
because H_X^a is empty; the second reduces to the retained rows of B(A).

### Raw helper

Take H_X^a=0 and H_Z^a=B(A). Then n_a=525 and k_a=302.
It has 225 supplied weight-7 Z checks of rank 223.

Its kernel splits as E(R^4) plus the two vectors

\[
 r_1=\omega(e_1+e_2),\quad r_2=\omega(e_1+e_5),\qquad
 \omega=1+x+\cdots+x^{74}.
\]

NUMERICAL: the measured image has dimension 302 modulo data X stabilizers.
The two extra embedded residual Xs commute with all canonical X/Z generators,
and add rank two even after adjoining all 1,200 canonical Xs and data X checks.
They therefore measure only the residual subsystem. This is admissible as
declared residual-state preparation in a fresh factory block, but is NOT
the exact 300-only nondemolition interface originally requested.

### Strict helper

Append to B(A) two rows measuring Z parity over all 75 positions of base
coordinate fibre 2, and all 75 positions of fibre 5. H_X^a stays empty.
The 227 supplied rows have rank 225, so k_a=300.

NUMERICAL: its entire kernel equals E(R^4), and its data image is precisely
the 300 selected canonical Xs, with no residual observation. The two added
weight-75 checks are real costs: this is not a claim of an LDPC protected
helper or cheap fault-tolerant extraction.

## 4. Ideal preparation and complete measurement channel

PROVED: for V=ker(H_Z^a), preparing physical all-plus, measuring the commuting
Z checks, and applying an X syndrome correction prepares

\[
 |V\rangle=|V|^{-1/2}\sum_{v\in V}|v\rangle.
\]

Each ideal outcome syndrome lies in the image of H_Z^a, so a correction
exists. This procedure does not invoke the LP mixed-state primitive being
constructed. Data all-logical-zero initialization similarly begins with
physical zeros and CSS syndrome projection. Neither ideal projection
argument is itself a circuit-level FT preparation certificate.

After the helper-control CNOTs, a physical helper X-readout string b gives

\[
 K_b\ \propto\ \sum_{v\in V}(-1)^{b\cdot v}X_d(vC).
\]

PROVED: this is the projector onto the character specified by b of the
entire measured subgroup. No additional data information is observed once
that subgroup is fixed. It establishes the raw-302/strict-300 distinction
without enumerating 2^300 logical outcomes.

The canonical outcome for (j,a) is the parity of b against x^a E e_j.
Its sign is retained in the Pauli frame through autoCNOT. Starting from all
canonical zeros, the strict helper prepares 300 independent signed GHZ_4s.
The raw helper also does so on the canonical subsystem, while additionally
projecting two residual modes.

NUMERICAL: a separate 4/8-qubit dense calculation accepts both single-quartet
and all four two-quartet outcomes. As a negative control, measuring only the
product of the two Xs yields an eight-qubit GHZ, not two independent GHZ_4s.

## 5. Fault-tolerance obstruction and structural costs

PROVED: because H_X^a=0, a single helper Z immediately before X readout has no
helper syndrome. In particular, helper position 150 (zero-based; fibre 3,
cyclic position 0) pairs with exactly one selected canonical generator.
It flips that reported outcome, does not propagate through the helper-control
CNOT, and leads to the wrong Pauli-frame GHZ sign. It is not a Z stabilizer.
Thus d_Z=1 for both candidates and their one-shot FT admission is rejected.

NUMERICAL: all 525 single-helper-Z supports are nontrivial logicals. Depending
on the position, one such fault flips 1 through 156 canonical readout parities.
This is correlated measurement-sign damage, not physical spreading of that
Z fault into 156 data qubits, and not an estimate of logical failure rate.

| Structural quantity | Raw helper | Strict helper |
|---|---:|---:|
| Helper data qubits | 525 | 525 |
| Independent observed data Xs | 302 | 300 |
| Additional residual Xs | 2 | 0 |
| Supplied helper Z checks | 225 | 227 |
| Maximum helper check weight | 7 | 75 |
| Helper Z-check incidences | 1,575 | 1,725 |
| Helper-to-data CNOTs | 525 | 525 |
| Matching layers, unrestricted connectivity | 1 | 1 |
| Data plus helper, excluding QEC overhead | 10,125 | 10,125 |
| One ancilla per supplied data/helper check | 8,625 | 8,627 |

CHECK: the last row is a static counting convention, NOT a sufficient FT
syndrome schedule, a minimum ancilla count, or a complete factory footprint.
Verification ancillas, syndrome repetitions, routing, storage, decoder and
classical reaction are unpriced. Runtime, failure, FT-admitted concurrency,
and initialization-round fields are null.

PROVED for this restricted matching: the helper kernel maps injectively into
data X homology. Therefore adding a nonzero commuting helper X stabilizer
on these same 525 coordinates cannot preserve this code-to-code CNOT map:
its image would be a nontrivial data logical, not a data stabilizer.
Changing the auxiliary redundancy or the coupling map is required for that
kind of quantum protection. Repeated data measurement is a separate route.

## 6. Bounded follow-up, not an implemented FT result

CHECK: an algebraic r-fold X-repetition extension would use 525r helper
qubits, 525(r-1) XX links, repeated Z-check supports, and r matching layers
to the same data row. It can protect the readout direction algebraically,
but increases check weight and can introduce hook-error problems. This
extension is NOT implemented, optimized, or FT-certified in this cycle.

OPEN next question: construct a protected helper or a repeated-measurement
schedule with an explicit fault-distance/decoder argument; compare its
ancilla and round costs against the completed-seed surgery fallback.
Do not infer a RASCqL speedup from the one-layer unprotected interface.

## Reproducibility and review

- Input: experiments/manifests/E-20261001-001.json, no random seed.
- Code: src/ecdlp_ftqc/code_constructions/lp_ghz.py.
- Independent logical replay: src/ecdlp_ftqc/verification/lp_ghz.py.
- Run: .venv/Scripts/python.exe scripts/run_lp_ghz_cycle.py.
- Output: experiments/runs/T-20261001-001/summary.json and reproducibility.json.
- Starting commit: b30f42d8f8e70cebf6ac59e7feff8fd523fdf3e9, dirty working tree.
- Generated provenance records the interpreter, platform and input-code hashes.
- Exact full-binary reconstruction was also independently reproduced by a
  separate codex worker without reading the implementation. This is internal
  verification, not a substitute for Claude cross-review.
- Validation command outcomes and review state are recorded in the task session.
- Implementer focused/construction/replay/Hub suite: 41 passed. The full run collected
  during verifier development returned 506 passed, two known sibling-pin
  failures, and one stale-import failure. After freezing code, a fresh run of
  all three failing test files plus replay/Hub returned 60 passed and only the
  two sibling-pin failures. No claim of a completely clean final full-suite
  rerun is made. See the session for exact commands and source commits.
- Claude's subsequent review reports 46 focused/Hub passes and 528 full-suite
  passes with only the two known sibling-pin failures; Ruff, strict mypy and
  compileall passed, and summary.json regenerated byte-identically. These are
  reviewer results, not new runs performed during status synchronization.
