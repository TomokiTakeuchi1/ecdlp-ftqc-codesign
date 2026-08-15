# Cain et al. 2026: Shor with 10,000 reconfigurable atomic qubits

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2603.28627v1>
- Version: arXiv:2603.28627v1, submitted 2026-03-30
- Local PDF: `literature/papers/2603.28627v1.pdf`
- Reading status: initial full-paper triage; resource tables and circuit mapping not yet independently reconstructed

## Source-reported claims

- **LITERATURE:** The paper studies reconfigurable neutral-atom FTQC architectures with separate memory, processor, operation, and resource-state zones.
- **LITERATURE:** Its space-efficient and balanced variants store data in high-rate lifted-product memory codes, move bounded-width subcircuits into smaller processor codes, execute Pauli-based computation, and teleport data back to memory.
- **LITERATURE:** The sequential baseline decomposes a Clifford+Toffoli circuit into processor-sized subcircuits and charges memory--processor communication, PPMs, mid-circuit measurements, and CCZ-state use.
- **LITERATURE:** The time-efficient study replaces linear-depth ripple-carry addition with a logarithmic-depth carry-lookahead proxy, batches up to `P` parallel CCZ states, and assumes parallel logical PPM layers.
- **LITERATURE:** The paper reports approximately 26,000 physical qubits and 10 days for its fastest ECC-256 case at a 1 ms stabilizer-cycle time. This project has not reproduced that estimate.

## Derived project relevance

- **CONJECTURE:** This is the closest system-level reference for the planned Oratomic-style memory--processor architecture, subcircuit partitioning, and parallel carry-lookahead Month-1 study.
- **CHECK:** Reconstruct each subcircuit's logical width, Toffoli-layer demand, mid-circuit measurements, memory load/store PPMs, and CCZ demand as a time series instead of applying only the paper's amortized time-per-Toffoli values.
- **CHECK:** Treat processor capacity `P`, magic-state production, surgery/PPM capacity, and adder ancillas as separate resources; the same symbol must not silently stand for all executable parallelism.
- **CHECK:** Map the paper's lifted-product and bivariate-bicycle code choices to canonical LP and mitten-code backends only through explicit adapters.

## Important evidence limits

- **CHECK:** The time-efficient section states that it is an approximate estimate rather than a concrete circuit or instruction-set specification.
- **CHECK:** Its 20--30% processor/factory encoding rates and some parallel-gadget capabilities rely on upcoming work, so the 26,000-qubit case is an architecture target, not yet a fully closed implementation proof.
- **CHECK:** The abstract describes the 26,000-qubit P-256 runtime as a few days, while the main text and conclusion report 10 days; use the explicit 10-day table/model result until this wording is resolved.
- **OPEN:** Determine whether automorphism, transversal/fold-transversal gates, or parallel surgery can realize every assumed carry-lookahead layer for canonical LP and mitten codes at the quoted distance and failure budget.
