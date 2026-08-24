---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - glossary
updated: 2026-08-15
---

# Plain-language Glossary

[[Research Hub/Home|← Home]] · [[Research Hub/Architecture Map.canvas|Architecture Map]]

| Term | Meaning in this project |
|---|---|
| Hierarchical DAG | A dependency graph that keeps adders, modular arithmetic, point addition, and Full Shor as nested subcircuits instead of flattening everything into one enormous gate list. |
| Algorithmic critical path | The shortest possible dependency-limited execution time before architecture resource conflicts are imposed. |
| QCLA | Quantum carry-lookahead adder. It uses a prefix network of propagate and generate values to reduce source circuit depth at the cost of extra workspace and bursty parallel demand. |
| Source algorithmic layer | One conflict-free time slice in the admitted source circuit. It is not a QEC cycle until a backend supplies executable operations, capacities, and durations. |
| Resource-constrained schedule | A realizable ordering after processor capacity, supported operations, ancillas, communication, decoder reaction, and factory supply are enforced. |
| CQLU | The logical compute unit used to compile a subcircuit into code-supported measurements, gates, and ancilla operations. |
| PPM | Pauli-product measurement: a joint measurement of a specified logical Pauli product such as $X_1X_2$. Its exact support matters. |
| Seed surgery | A reusable lower-throughput surgery method used when a high-rate construction is not applicable. |
| Parallel/high-rate surgery | A code-specific construction that measures a supported family of Pauli products concurrently. It requires more than independent circuit gates: supports, conflicts, and extractor resources must all be legal. |
| Extractor ancilla | An encoded ancilla resource used to extract a logical Pauli-product outcome fault tolerantly. |
| Bridge ancilla | A temporary communication resource joining code blocks or zones; it is distinct from the operation area where a gate or measurement is executed. |
| Memory I/O | Loading logical states from memory to the processor and storing them back, including teleportation, measurement, and frame updates. |
| Frame tracking | Recording known Pauli or Clifford corrections classically instead of physically applying them immediately, when later operations and measurements permit it. |
| Factory demand trace | The time series of T/CCZ consumption. It preserves bursts that an average consumption rate would hide. |
| Source occupancy | Logical values already required by the input circuit. Compiler-generated ancillas must be added before claiming executable capacity. |
| Evidence label | A marker such as `LITERATURE`, `NUMERICAL`, or `CHECK` that states how strongly a research claim is supported. |
