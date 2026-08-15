# Zheng et al. 2026: logical computation with canonical lifted-product codes

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2607.28605v1>
- Version: arXiv:2607.28605v1, submitted 2026-07-30
- Local PDF: `literature/papers/2607.28605v1.pdf`
- Reading status: abstract-level triage; full construction not yet audited

## Source-reported claims

- **LITERATURE:** The paper defines a canonical logical basis for a cyclic-symmetry family of lifted-product qLDPC codes.
- **LITERATURE:** The abstract reports constant-depth automorphism and fold-transversal Clifford gates, modular graph-code surgery, highly parallel logical Pauli-product measurements, and parallel magic-state injection.
- **LITERATURE:** Example code parameters include `[[1122,148,<=20]]` and `[[4350,1224,<=20]]`, with a small number of reusable seed-surgery gadgets; the stated distance is an upper-bound notation in the abstract, not a verified exact distance here.

## Derived project relevance

- **CONJECTURE:** This is a high-priority candidate instruction-set paper for Months 1--2 because it may connect a dense logical register directly to PPM concurrency and injection bandwidth.
- **CHECK:** The architecture model must extract which logical Pauli supports can be measured simultaneously, extractor ancilla size, surgery duration, locality/reconfiguration assumptions, and decoder/reaction latency.
- **CHECK:** “Constant depth” must not be converted to constant physical time until syndrome rounds and classical feed-forward are specified.

## Open interpretation questions

- **OPEN:** What finite-size logical failure rates are established for the example blocks and gadgets?
- **OPEN:** Can the supported PPM family express the ECDLP adder/inversion dependency pattern without excessive permutation or memory traffic?
- **OPEN:** What factory footprint and routing cost accompany parallel injection into many logical qubits?
