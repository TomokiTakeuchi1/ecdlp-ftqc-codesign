# Bhardwaj et al. 2026: high-rate qLDPC processors

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2607.28795v1>
- Version: arXiv:2607.28795v1, submitted 2026-07-30
- Local PDF: `literature/papers/2607.28795v1.pdf`
- Reading status: Tables I--V, X--XI and Appendices C--E/I audited for `T-20260815-002`

## Source-reported claims

- **LITERATURE:** The paper introduces non-abelian “mitten” qLDPC processor codes with a stated 20% encoding rate and check weight 9.
- **LITERATURE:** The abstract reports a modular Clifford toolkit, high-rate parallel logical measurements, and parallel magic-state injection.
- **LITERATURE:** Under circuit-level noise, it reports block-level results including `[[300,60,14]]` near `1e-11` per round at 0.1% physical error and `[[975,195,<=24]]` near `1e-8` at 0.4% physical error.
- **LITERATURE:** The reported decoder has sub-millisecond average latency per logical cycle and is positioned for neutral-atom hardware.
- **LITERATURE:** For `[[300,60,14]]`, Table II reports seed-gadget data-ancilla counts `43/100/43/100/100` for `X/Y/Z/XX/ZZ`; the added check counts are recorded in `configs/codes/mitten_j300_k60_d14_v1.yaml`.
- **LITERATURE:** Figure 2 simulates single-X surgery with `R=11`, XX surgery with `R=13`, and a ten-product high-rate XX gadget with `R=13` merged-code syndrome rounds.
- **LITERATURE:** Table III constructs J300 high-rate XX gadgets for exactly 10, 20, and 30 disjoint products, adding respectively 601, 881, and 1,274 gadget qubits. Only the ten-product instance has the Figure-2 runtime/error experiment used by backend v1.
- **LITERATURE:** Table IV reports 780 gadget qubits plus 382 X-check and 372 Z-check additions for the J300 full extractor, but not its operation duration.
- **LITERATURE:** Table X reports a 678 microsecond average memory-decoder latency for J300 under a 1 ms assumed syndrome cycle; this is not a worst-case feed-forward bound and is not used as the v1 reaction time.
- **LITERATURE:** Table XI estimates J300 neutral-atom syndrome-cycle times of 10.98 ms with two crossed-AOD pairs, 7.22 ms with four pairs, and 3.47 ms with an idealized fast SLM.

## Derived project relevance

- **CONJECTURE:** These finite-size rates make the paper a leading candidate for the Month-2 tens-of-thousands-physical-qubit architecture screen.
- **CHECK:** Separate per-block/per-round error, surgery logical error, injection error, and full-algorithm failure; none is interchangeable.
- **CHECK:** Model measurement concurrency, seed-gadget/extractor occupancy, decoder throughput distribution, and routing rather than using the 20% code rate alone.
- **CHECK:** The source proves universality through PPMs and injection but does not supply the application-specific PBC trace for Gidney's CNOT/H/S/T sequence. Do not label an intra-block CNOT as transversal.
- **CHECK:** `R` counts merged-code syndrome rounds; separately account for gadget preparation/readout, decoder reaction, and hardware reconfiguration before converting a schedule to seconds.

## Open interpretation questions

- **OPEN:** How many data blocks, extractors, surgery ancillas, factory blocks, and spare atoms are required for a 1200--1500 logical-qubit ECDLP workload?
- **OPEN:** Is the reported logical-operation budget compatible with tens of millions of ECDLP non-Clifford instructions after union-bound and correlated-failure accounting?
- **OPEN:** What physical cycle and tail-latency assumptions turn sub-millisecond average decode time into executable wall-clock time?
