# Yang et al. 2026: RASCqL complex qLDPC logic units

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2602.14273v2>
- Version: arXiv:2602.14273v2, revised 2026-03-08
- Local PDF: `literature/papers/2602.14273v2.pdf`
- Reading status: abstract triage plus Section 4/Table 2 instruction and timing audit for `T-20260905-001`

## Source-reported claims

- **LITERATURE:** RASCqL is presented as a reaction-time-limited, application-tailored qLDPC architecture for complex logical instructions.
- **LITERATURE:** The abstract reports `2x`--`7x` footprint reductions with spacetime volume comparable to transversal surface-code architectures for selected workloads.
- **LITERATURE:** Complex Clifford transformations are embedded through code automorphisms, with reconfigurable neutral-atom parallelism used for QEC and transversal operations.
- **LITERATURE:** End-to-end studies are reported for factoring and quantum chemistry over physical error rates around `2e-3` to `5e-4`.
- **LITERATURE:** For the paper's `[[450,32,8]]` HGPS/RNAA instance, Table 1 reports a `3.9 ms` QEC cycle. Table 2 reports virtual autoCNOT and dirty-shift operations at zero online execution time, `3.0 ms` for a blockwise transversal CNOT, `1.9 ms` for global H-SWAP, and `0.5 ms` for global X- or Z-basis measurement. A virtual relabeling may add up to `2.4 ms` before the next transversal CNOT.
- **LITERATURE:** Table 2 reports provisioned reactive PPM execution at `6.0 ms`; without the assumed offline state preparation the displayed total is `44.2 ms`. Mixed `|0>`/`|+>` preparation is likewise `6.0 ms` online and `31.7 ms` without provisioning. These are source-domain RNAA times, not portable logical-cycle constants.
- **LITERATURE:** Appendix C.3 describes H-SWAP as Hadamard on all logical qubits together with a logical transpose. It is therefore global/SIMD rather than arbitrary subset-addressable H.
- **LITERATURE:** Section 4.2 embeds a limited four-bit `g_auto` CNOT pattern and dirty cyclic shifts as virtual automorphisms. It does not claim arbitrary sparse CNOT addressability. Section 4.3 instead uses repeated `g_auto`, global H, blockwise tCNOTs, and provisioned GHZ states for its arithmetic motifs.

## Derived project relevance

- **CONJECTURE:** This is the most direct user-supplied reference for the Month-1 “complex logical instruction” hypothesis and should be tested against ECDLP arithmetic rather than assuming factoring results transfer.
- **CHECK:** Map each QCLA CNOT-layer GF(2) transformation to the exact generated RASCqL automorphism ISA; zero online time is conditional on successful membership, not a generic CNOT cost.
- **CHECK:** Compare the ECDLP arithmetic critical path both with and without the embedded complex Clifford operations; the quoted footprint factor alone is not a runtime model.
- **CHECK:** Treat the `1.9/3.0/0.5 ms` values only as a same-source-domain comparator until direct-CCZ consumption, target-mask packing, decoder service, and movement are closed in one HGPS/RNAA contract.

## Open interpretation questions

- **OPEN:** Which adder or modular-arithmetic blocks map natively, and what ECDLP-specific code specialization is required?
- **OPEN:** How are data movement, atom rearrangement, decoding, and non-Clifford state supply represented in the reported end-to-end estimates?
- **OPEN:** Does specialization reduce flexibility enough to increase full-Shor scheduling or memory costs?
- **OPEN:** Can the QCLA H target masks be packed so every occupied HGPS logical lane should receive H while preserving the direct-CCZ correction-frame convention?
