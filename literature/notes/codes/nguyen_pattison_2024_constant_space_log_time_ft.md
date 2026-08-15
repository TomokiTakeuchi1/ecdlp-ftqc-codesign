# Nguyen and Pattison 2024/2025: constant-space, logarithmic-time fault tolerance

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2411.03632v2>
- Version: arXiv:2411.03632v2, revised 2025-08-14
- Local PDF: `literature/papers/2411.03632v2.pdf`
- Reading status: abstract-level theoretical triage; constants and finite-size constructions not yet audited

## Source-reported claims

- **LITERATURE:** In a model with quick, noiseless polyloglog-time auxiliary classical computation, the paper constructs constant-space and approximately logarithmic-time fault-tolerance overhead using constant-rate qLTC/qLDPC ingredients.
- **LITERATURE:** It includes a qudit Reed--Solomon magic-state distillation construction, parallel single-shot decoding results, logical state preparation/gates, and a weight-enumerator composition framework.
- **LITERATURE:** The stated result is asymptotic and explicitly depends on a strong classical-computation model.

## Derived project relevance

- **CONJECTURE:** This paper is a theoretical lower-overhead reference and a source of compositional failure-analysis tools, not a near-term finite-size architecture specification.
- **CHECK:** Before using it in Months 2--3, identify all hidden constants, block sizes, nonlocal connectivity, qudit-to-qubit conversion, classical depth/throughput, and decoder assumptions.
- **CHECK:** Do not combine its asymptotic overhead with finite-size qLDPC logical-error rates from another paper without an explicit adapter model.

## Open interpretation questions

- **OPEN:** At ECDLP-scale logical operation counts, do available finite instances enter the claimed asymptotic regime?
- **OPEN:** Can the noiseless classical auxiliary assumption be replaced with a concrete decoder/controller budget?
- **OPEN:** Is the weight-enumerator formalism practical for composing arithmetic gadgets, factories, and memory operations in this project?
