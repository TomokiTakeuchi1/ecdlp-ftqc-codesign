# ECDLP-256 FTQC Architecture窶鄭lgorithm Co-Design

This repository studies end-to-end resource estimation and architecture窶殿lgorithm co-design for Shor's algorithm applied to 256-bit elliptic-curve discrete logarithms.

## Central question

How much of the logical parallelism in ECDLP-256 circuits can be converted into actual wall-clock speedup under realistic constraints from:

- quantum error-correcting codes,
- memory and processor organization,
- fault-tolerant logical operations,
- magic-state or resource-state factories,
- decoding, feed-forward, routing, and communication,
- and the arithmetic structure of the algorithm?

## Primary outputs

1. Reproducible circuit and metadata traces.
2. Architecture-aware schedulers and lower/upper bounds.
3. Physical-qubit and runtime Pareto frontiers.
4. Bottleneck decompositions across algorithm, processor, I/O, logical operations, and factories.
5. Design recommendations for heterogeneous FTQC architectures.

## Start here

Read these files in order:

1. `AGENTS.md`
2. `context/PROJECT_CHARTER.md`
3. `context/STATUS.md`
4. `context/TASKS.md`
5. `coordination/PROTOCOL.md`

Generated data belong in `experiments/runs`, `benchmarks/results`, or `outputs`; do not commit large generated artifacts unless explicitly approved.