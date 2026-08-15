# Zhao et al. 2026: ultra-high-rate QEC on reconfigurable atom arrays

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2604.16209v2>
- Version: arXiv:2604.16209v2, revised 2026-06-26
- Local PDF: `literature/papers/2604.16209v2.pdf`
- Reading status: abstract-level triage; syndrome schedule and decoder resource model not yet audited

## Source-reported claims

- **LITERATURE:** The paper co-designs an ultra-high-rate code family with reconfigurable neutral-atom implementation constraints and reports encoding rates above one half.
- **LITERATURE:** Under a circuit-level noise model at 0.1% physical error, the abstract reports per-logical-per-round error estimates around `1.3e-13` for `[[2304,1156,<=14]]` and `2.9e-11` for `[[1152,580,<=12]]`, with stated confidence intervals.
- **LITERATURE:** Syndrome extraction, atom rearrangement, and a hierarchical decoder are included in the claimed implementation story.

## Derived project relevance

- **CONJECTURE:** The reported finite blocks are direct candidates for the Month-2 physical-qubit feasibility bound because two large blocks could encode roughly the logical width of the current ECDLP source circuit.
- **CHECK:** A code-rate calculation alone omits syndrome ancillas, movement zones, spare atoms, extractor/surgery ancillas, factories, and logical-operation gadgets.
- **CHECK:** Convert per-logical-per-round error to a full-algorithm budget using the actual number of rounds and correlated/block failure semantics, not only logical operation count.

## Open interpretation questions

- **OPEN:** Which logical Clifford, PPM, measurement, and injection operations are natively available on these blocks, with what time and failure rate?
- **OPEN:** What atom-movement schedule and decoder throughput are required under the ECDLP arithmetic demand trace?
- **OPEN:** Does reserving enough capacity for operations and factories erase the greater-than-one-half data-code rate advantage?
