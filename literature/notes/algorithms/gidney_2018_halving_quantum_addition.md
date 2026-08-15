# Gidney 2018: halving the cost of quantum addition

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/1709.06648v3>
- Version: arXiv:1709.06648v3, revised 2018-06-13
- Local PDF: `literature/papers/1709.06648v3.pdf`
- Reading status: abstract and first-page triage; full circuit audit pending

## Source-reported claims

- **LITERATURE:** The temporary logical-AND construction uses four T gates to compute an AND into an ancilla and zero T gates to erase it by measurement-assisted uncomputation.
- **LITERATURE:** The paper reports an n-bit adder with T count `4n + O(1)` and an n-bit controlled adder with T count `8n + O(1)`.
- **LITERATURE:** The construction deliberately trades non-Clifford gates for measurements and classical corrections, so T count alone does not determine executable runtime.

## Derived project relevance

- **CONJECTURE:** This is the natural Month-1 ripple-carry arithmetic baseline, provided the exact register, measurement, reset, and feed-forward semantics are preserved in the trace.
- **CHECK:** The project must pin one exact finite-size circuit generator before treating the asymptotic counts as a 256-bit regression target.
- **CHECK:** T-state and CCZ-state lowerings must remain separate because their injection and correction schedules differ across backends.

## Open interpretation questions

- **OPEN:** Which controlled-adder decomposition should be used for the canonical 256-bit trace?
- **OPEN:** How much of the measurement-assisted uncomputation latency can overlap with memory I/O and decoding?
- **OPEN:** Does a PPM-oriented lowering expose useful high-rate-surgery batches, or is the ripple dependency dominant?
