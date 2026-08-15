# Bhardwaj et al. 2026: high-rate qLDPC processors

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2607.28795v1>
- Version: arXiv:2607.28795v1, submitted 2026-07-30
- Local PDF: `literature/papers/2607.28795v1.pdf`
- Reading status: abstract-level triage; decoder and surgery data not yet audited

## Source-reported claims

- **LITERATURE:** The paper introduces non-abelian “mitten” qLDPC processor codes with a stated 20% encoding rate and check weight 9.
- **LITERATURE:** The abstract reports a modular Clifford toolkit, high-rate parallel logical measurements, and parallel magic-state injection.
- **LITERATURE:** Under circuit-level noise, it reports block-level results including `[[300,60,14]]` near `1e-11` per round at 0.1% physical error and `[[975,195,<=24]]` near `1e-8` at 0.4% physical error.
- **LITERATURE:** The reported decoder has sub-millisecond average latency per logical cycle and is positioned for neutral-atom hardware.

## Derived project relevance

- **CONJECTURE:** These finite-size rates make the paper a leading candidate for the Month-2 tens-of-thousands-physical-qubit architecture screen.
- **CHECK:** Separate per-block/per-round error, surgery logical error, injection error, and full-algorithm failure; none is interchangeable.
- **CHECK:** Model measurement concurrency, seed-gadget/extractor occupancy, decoder throughput distribution, and routing rather than using the 20% code rate alone.

## Open interpretation questions

- **OPEN:** How many data blocks, extractors, surgery ancillas, factory blocks, and spare atoms are required for a 1200--1500 logical-qubit ECDLP workload?
- **OPEN:** Is the reported logical-operation budget compatible with tens of millions of ECDLP non-Clifford instructions after union-bound and correlated-failure accounting?
- **OPEN:** What physical cycle and tail-latency assumptions turn sub-millisecond average decode time into executable wall-clock time?
