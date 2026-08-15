# Zhou et al. 2025: transversal architecture for reconfigurable atom arrays

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2505.15907v1>
- Version: arXiv:2505.15907v1, submitted 2025-05-21
- Local PDF: `literature/papers/2505.15907v1.pdf`
- Reading status: initial full-paper triage; arithmetic unit and error-model details not yet reconstructed

## Source-reported claims

- **LITERATURE:** The paper proposes a low-overhead FTQC architecture for dynamically reconfigurable neutral-atom arrays using fast transversal logical operations.
- **LITERATURE:** Its functional blocks include magic-state factories, quantum-arithmetic units, and quantum lookup tables, with layouts designed to reduce atom-movement time and correlated-decoding volume.
- **LITERATURE:** Under the paper's stated assumptions, transversal operations provide a runtime improvement scaling with code distance relative to its comparison baseline.
- **LITERATURE:** The reported RSA-2048 case uses 19 million physical qubits and 5.6 days at a 1 ms QEC-cycle time. This project has not reproduced that estimate.

## Derived project relevance

- **CONJECTURE:** This is a primary Month-1 architecture reference for mapping the parallel carry-lookahead adder DAG to transversal arithmetic units in a memory--processor design.
- **CHECK:** Extract the exact adder construction, logical block/code assumptions, transversal gadget timing, movement schedule, and permitted overlap before using the paper as an executable backend model.
- **CHECK:** Compare its code and layout assumptions explicitly with canonical lifted-product and mitten-code candidates; do not transfer the RSA resource totals directly to ECDLP-256.
- **CHECK:** Keep arithmetic critical-path reduction separate from processor capacity, load/store traffic, decoding latency, classical reaction time, factory supply, and routing constraints.

## Open interpretation questions

- **OPEN:** Which carry-lookahead primitives are implemented directly as transversal functional-unit operations, and which require injection or decomposed Clifford+T execution?
- **OPEN:** What processor footprint and memory bandwidth are required when the arithmetic unit is reused across segmented ECDLP subcircuits?
- **OPEN:** How should correlated-decoding volume and atom movement be converted into a conservative runtime and failure-budget model for canonical LP or mitten codes?
