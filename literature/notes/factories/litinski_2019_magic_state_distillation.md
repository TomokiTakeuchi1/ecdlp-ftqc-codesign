# Litinski 2019: magic-state distillation overhead

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/1905.06903v3>
- Version: arXiv:1905.06903v3, revised 2019-11-06
- Journal: *Quantum* 3, 205 (2019), DOI `10.22331/q-2019-12-02-205`
- Local PDF: `literature/papers/1905.06903v3.pdf`
- Reading status: abstract-level triage; protocols and tables not yet parameterized

## Source-reported claims

- **LITERATURE:** The paper separates error-detecting and non-error-detecting portions of distillation circuits so that many factory qubits can use lower code distance.
- **LITERATURE:** It argues that this reduces both factory qubit footprint and spacetime cost, sometimes below the cost of a full-distance logical Clifford operation.
- **LITERATURE:** Version 2 corrected a protocol error and revised overhead estimates; version 3 added faulty-T-measurement analysis. Only v3 should seed the model.

## Derived project relevance

- **CONJECTURE:** This is a useful Month-3 surface-code factory baseline, not evidence that factories are negligible for qLDPC ECDLP execution.
- **CHECK:** Parameterize protocol, input/output error, acceptance probability, code distances by subregion, cycle time, output cadence, warm-up, footprint, and buffer interface.
- **CHECK:** Translate the ECDLP circuit's distinct CCX, CCZ, AND, and T-like demands before selecting a T-state factory; direct CCZ/Toffoli resources may change the comparison.

## Open interpretation questions

- **OPEN:** Which protocol and code-distance allocation minimize total qubits subject to the full ECDLP failure budget?
- **OPEN:** How much buffering is required under bursty arithmetic consumption, and does routing/injection become the bottleneck?
- **OPEN:** What remains valid when the data code and factory code are different families?
