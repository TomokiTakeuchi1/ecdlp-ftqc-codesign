# Draper et al. 2006: logarithmic-depth quantum carry-lookahead addition

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/quant-ph/0406142v1>
- Version: arXiv:quant-ph/0406142v1, submitted 2004-06-20; journal publication 2006
- Local PDF: `literature/papers/quant-ph-0406142v1.pdf`
- Reading status: abstract and first-page triage; finite-size circuit tables not yet audited

## Source-reported claims

- **LITERATURE:** The QCLA adder has `O(log n)` depth and uses `O(n)` ancilla qubits.
- **LITERATURE:** The paper provides in-place and out-of-place variants and addition modulo both `2^n` and `2^n - 1`.
- **LITERATURE:** Its advantage over ripple carry is algorithmic depth, not automatically resource-constrained FTQC runtime.

## Derived project relevance

- **CONJECTURE:** QCLA is a high-priority Month-1 parallel-adder candidate because its propagate/generate and prefix-tree stages provide explicit concurrency for processor and surgery scheduling studies.
- **CHECK:** The exact 256-bit variant, gate decomposition, ancilla convention, and controlled semantics must be pinned before comparison with Gidney ripple carry.
- **CHECK:** Processor partitioning may erase the logarithmic-depth advantage through ancilla pressure, memory traffic, and inter-block PPMs.

## Open interpretation questions

- **OPEN:** Which in-place or out-of-place QCLA variant best matches the point-addition register contract?
- **OPEN:** How many prefix operations remain compatible with the concrete canonical LP or mitten high-rate-surgery patterns?
- **OPEN:** What is the finite-size depth and peak live-ancilla count at `n = 256` under the selected Toffoli or PPM lowering?
