# Kim et al. 2026: new depth-oriented ECDLP circuits

- Task: `T-20260811-002`
- Source: <https://eprint.iacr.org/2026/106>
- Version: IACR ePrint 2026/106, revision observed 2026-05-26
- Local PDF: `literature/papers/eprint-2026-106-rev-2026-05-26.pdf`
- Reading status: abstract and first-page triage; circuit and physical-resource assumptions not yet audited

## Source-reported claims

- **LITERATURE:** The paper presents depth-oriented point-addition circuits using in-place affine and out-of-place projective-coordinate constructions.
- **LITERATURE:** The abstract reports improvements in qubit-count-times-T-depth and qubit-count-times-full-depth products relative to selected earlier ECDLP circuits.
- **LITERATURE:** For P-224, the abstract reports tradeoff points of about 107 million physical qubits for 1.4 minutes or about 670,000 physical qubits for 14.3 hours.

## Derived project relevance

- **CONJECTURE:** The circuits are relevant as a depth-oriented comparison for the Month-2 full-Shor workload and may provide an alternative source of point-addition hierarchy.
- **CHECK:** The P-224 physical-resource points must not be transferred to ECDLP-256 or to the project's qLDPC memory--processor architecture without reconstructing the hardware, QEC, factory, and timing assumptions.
- **CHECK:** The exact controlled point-addition semantics, exceptional-case handling, circuit artifacts, and finite-size counts require full-paper audit before baseline use.

## Open interpretation questions

- **OPEN:** Are machine-readable circuit generators or complete gate traces publicly available?
- **OPEN:** Which components produce the reported depth reductions, and do they expose PPM batches compatible with canonical LP or mitten processors?
- **OPEN:** How do its physical estimates allocate factory, routing, decoding, and classical reaction costs?
