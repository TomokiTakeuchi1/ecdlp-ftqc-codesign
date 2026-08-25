# Selinger 2013: exact Clifford+T Toffoli baseline

- Task: `T-20260825-001`
- Source: <https://arxiv.org/abs/1210.0974v2>
- Version: arXiv:1210.0974v2, revised 2013-04-03
- Local PDF: `literature/papers/1210.0974.pdf`
- SHA-256: `5C1FBC4571B48F6E6893A8D15045509A08AB5C6764276B44BA1AC69C528129E2`
- Reading status: pages 1--2, circuits (1)--(4), and Figure 1 audited directly

## Admitted construction

- **LITERATURE:** Circuit (1) is the selected ancilla-free exact Toffoli
  decomposition. It has seven T-family gates, six CNOTs, two Hadamards, and
  one S gate. In the orientation transcribed here the phase gates are three T
  and four T-dagger.
- **LITERATURE:** The exact drawing has T-depth 6; the paper's circuit (2)
  reduces this to T-depth 4 by commutations. The compiler retains circuit (1)
  and its two explicitly disjoint two-gate columns rather than claiming an
  optimized source depth.
- **NUMERICAL:** An independent 8-by-8 unitary reconstruction matches ideal
  CCX up to global phase with maximum absolute error
  `2.220446049250313e-16`.

## Alternatives not admitted

- **LITERATURE:** Figure 1 gives a T-depth-one Toffoli using four ancillas.
  It is not used because those ancillas would change the resident-capacity and
  high-rate comparison.
- **LITERATURE:** Equation (4) relates CCX to doubly controlled Z by a target
  basis change. This motivates a future direct-CCZ implementation comparator.
- **OPEN:** No direct CCZ injection, CCZ factory, routing, buffering, or
  failure model is selected in this cycle. Therefore the seven-T route is a
  semantic baseline, not a dominance claim.
