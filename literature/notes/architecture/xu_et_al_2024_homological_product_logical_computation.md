# Xu et al. 2024: parallel logical computation with homological-product codes

- Task: `T-20260811-002`
- Source: <https://arxiv.org/abs/2407.18490v1>
- Version: arXiv:2407.18490v1, submitted 2024-07-26
- Local PDF: `literature/papers/2407.18490v1.pdf`
- Reading status: Figure 11 and the CNOT/PPM compilation discussion audited for `T-20260815-004`; Figures 5--6 and the quantum-adder section audited for `T-20260824-001`

## Source-reported claims

- **LITERATURE:** The construction performs parallel logical Pauli-product measurements through transversal CNOTs between a data qLDPC code and a constructed ancilla code.
- **LITERATURE:** Hypergraph-product codes support parallel PPMs on a logical subgrid; 3D and 4D generalizations are described as supporting constant-depth PPMs.
- **LITERATURE:** The paper explicitly builds GHZ/magic-state primitives and parallel quantum adders, and targets reconfigurable hardware such as neutral-atom arrays.
- **LITERATURE:** Figure 11(c) gives a measurement-based CNOT using one `|+>` ancilla, `ZZ` and `XX` Bell measurements, a final ancilla-Z measurement, and Pauli corrections `Z_control^b X_target^(a+c)`.
- **LITERATURE:** Figure 11(a) records one-bit state teleportation, while Figure 11(b) gives a teleported S construction using an `|i>` stabilizer ancilla.
- **LITERATURE:** The Figure-6 adder follows the Active Volume variant of the
  Gidney ripple-carry circuit, with `k-1` temporary-AND Toffolis and bridge
  Bell pairs connecting adjacent bit segments.
- **LITERATURE:** Five HGP data-patch families encode the `a`, `b`, `c`, `d`,
  and `e` qubit types. Six additional ancilla patches support the reactive
  measurements; these patch counts are not a single-block logical-qubit count.
- **LITERATURE:** Segment bodies and temporary-AND consumptions are parallelized,
  but final reactive measurements on the ancilla patches remain sequential.
  The source reports scaling `c1 sqrt(k) log(k) + c2 k` logical cycles and does
  not give the constants needed for an executable finite-size runtime.

## Derived project relevance

- **CONJECTURE:** This is a primary Month-1 source for translating adder dependency structure into a bounded-parallel PPM schedule.
- **CHECK:** Extract finite HGP patch sizes, PPM layer durations, preparation
  latency, routing, and the constants `c1,c2` before promoting the Figure-6
  construction from dependency/resource sensitivity to executable runtime.
- **CHECK:** Keep algorithmic PPM parallelism separate from executable parallelism after shared ancillas, syndrome rounds, routing, and reaction constraints.
- **CHECK:** Figure 11 fixes logical channel identities but not J300 Mitten syndrome-round durations, preparation space, or reaction latency. Those quantities cannot be imported from the HGP implementation without a separate code mapping.

## Open interpretation questions

- **OPEN:** Which ECDLP arithmetic motifs benefit most: ripple-carry addition, carry-lookahead, multiplication, or EEA control?
- **OPEN:** How does the ancilla construction scale at the 256-bit register size and under repeated in-place arithmetic?
- **OPEN:** Can the magic-state teleportation construction sustain burst demand without dominating memory and processor occupancy?
