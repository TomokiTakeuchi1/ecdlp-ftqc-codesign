# Guyot and Jaques 2026: addressability on CSS codes

- Task: `T-20260905-001`
- Source: <https://quantum-journal.org/papers/q-2026-06-30-2145/>
- Version: Quantum 10, 2145 (2026); arXiv:2502.13889v4
- Reading status: theorem-scope audit for H/CNOT option screening

## Source-reported claims

- **LITERATURE:** The paper studies circuits that implement a logical gate on a strict subset of logical qubits of a CSS code.
- **LITERATURE:** Under its stated non-splitting, nonzero-rate, distance-preserving, and 1-local Clifford hypotheses, it gives no-go results for addressing H and related single-qubit Clifford gates to a nonempty strict logical subset.
- **LITERATURE:** It also gives a CNOT/CZ no-go result between sufficiently high-rate codes under a more restrictive circuit condition called global by the authors.
- **LITERATURE:** The results are conditional theorem statements; they do not rule out targeted circuits using broader Clifford sequences, code deformation, gauge fixing, teleportation, or deliberately specialized code families.

## Derived project relevance

- **CHECK:** A global H-SWAP primitive should not be relabeled as subset-addressable H. QCLA needs an explicit block-packing, code-switching, or teleportation fallback.
- **CHECK:** A blockwise transversal CNOT should not be relabeled as an arbitrary sparse set of logical CNOT pairs. Pair packing and logical-basis alignment are separate mapper obligations.
- **CONJECTURE:** Embedding whole QCLA CNOT-layer transformations, rather than individual CNOTs, is the more plausible high-rate co-design target because the source layers are structured disjoint matchings.

## Open interpretation questions

- **OPEN:** Which theorem hypotheses hold for the eventual direct-CCZ high-rate code family?
- **OPEN:** Can application-specific automorphisms implement all required QCLA layer matrices without unacceptable rate, check-weight, distance, or movement penalties?
