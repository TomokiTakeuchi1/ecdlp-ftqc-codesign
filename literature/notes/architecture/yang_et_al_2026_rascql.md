# Yang et al. 2026: RASCqL complex qLDPC logic units

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2602.14273v2>
- Version: arXiv:2602.14273v2, revised 2026-03-08
- Local PDF: `literature/papers/2602.14273v2.pdf`
- Reading status: abstract-level triage; resource tables and assumptions not yet audited

## Source-reported claims

- **LITERATURE:** RASCqL is presented as a reaction-time-limited, application-tailored qLDPC architecture for complex logical instructions.
- **LITERATURE:** The abstract reports `2x`--`7x` footprint reductions with spacetime volume comparable to transversal surface-code architectures for selected workloads.
- **LITERATURE:** Complex Clifford transformations are embedded through code automorphisms, with reconfigurable neutral-atom parallelism used for QEC and transversal operations.
- **LITERATURE:** End-to-end studies are reported for factoring and quantum chemistry over physical error rates around `2e-3` to `5e-4`.

## Derived project relevance

- **CONJECTURE:** This is the most direct user-supplied reference for the Month-1 “complex logical instruction” hypothesis and should be tested against ECDLP arithmetic rather than assuming factoring results transfer.
- **CHECK:** Record the exact instruction semantics, supported code modifications, compilation overhead, reaction time, physical cycle, code rate, and workload-specific assumptions.
- **CHECK:** Compare the ECDLP arithmetic critical path both with and without the embedded complex Clifford operations; the quoted footprint factor alone is not a runtime model.

## Open interpretation questions

- **OPEN:** Which adder or modular-arithmetic blocks map natively, and what ECDLP-specific code specialization is required?
- **OPEN:** How are data movement, atom rearrangement, decoding, and non-Clifford state supply represented in the reported end-to-end estimates?
- **OPEN:** Does specialization reduce flexibility enough to increase full-Shor scheduling or memory costs?
