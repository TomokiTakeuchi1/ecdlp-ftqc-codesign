# Xu et al. 2024: parallel logical computation with homological-product codes

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2407.18490v1>
- Version: arXiv:2407.18490v1, submitted 2024-07-26
- Local PDF: `literature/papers/2407.18490v1.pdf`
- Reading status: Figure 11 and the CNOT/PPM compilation discussion audited for `T-20260815-004`; full adder construction not yet reconstructed

## Source-reported claims

- **LITERATURE:** The construction performs parallel logical Pauli-product measurements through transversal CNOTs between a data qLDPC code and a constructed ancilla code.
- **LITERATURE:** Hypergraph-product codes support parallel PPMs on a logical subgrid; 3D and 4D generalizations are described as supporting constant-depth PPMs.
- **LITERATURE:** The paper explicitly builds GHZ/magic-state primitives and parallel quantum adders, and targets reconfigurable hardware such as neutral-atom arrays.
- **LITERATURE:** Figure 11(c) gives a measurement-based CNOT using one `|+>` ancilla, `ZZ` and `XX` Bell measurements, a final ancilla-Z measurement, and Pauli corrections `Z_control^b X_target^(a+c)`.
- **LITERATURE:** Figure 11(a) records one-bit state teleportation, while Figure 11(b) gives a teleported S construction using an `|i>` stabilizer ancilla.

## Derived project relevance

- **CONJECTURE:** This is a primary Month-1 source for translating adder dependency structure into a bounded-parallel PPM schedule.
- **CHECK:** Extract the exact adder family, logical width, PPM supports, PPM layer count, ancilla-code size, preparation latency, and permitted overlap between PPMs.
- **CHECK:** Keep algorithmic PPM parallelism separate from executable parallelism after shared ancillas, syndrome rounds, routing, and reaction constraints.
- **CHECK:** Figure 11 fixes logical channel identities but not J300 Mitten syndrome-round durations, preparation space, or reaction latency. Those quantities cannot be imported from the HGP implementation without a separate code mapping.

## Open interpretation questions

- **OPEN:** Which ECDLP arithmetic motifs benefit most: ripple-carry addition, carry-lookahead, multiplication, or EEA control?
- **OPEN:** How does the ancilla construction scale at the 256-bit register size and under repeated in-place arithmetic?
- **OPEN:** Can the magic-state teleportation construction sustain burst demand without dominating memory and processor occupancy?
