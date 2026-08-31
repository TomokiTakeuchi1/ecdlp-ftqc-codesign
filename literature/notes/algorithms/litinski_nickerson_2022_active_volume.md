# Litinski and Nickerson 2022: Active Volume

- Task: `T-20260824-001`
- Source: <https://arxiv.org/abs/2211.15465v1>
- Version: arXiv:2211.15465v1, submitted 2022-11-28
- Local PDF: `literature/papers/2211.15465v1.pdf`
- SHA-256: `BF305E578AEFC986F4E74110EF55155E7C9711401B7D4E18BCB63BE304D2BC45`
- Reading status: Figures 10, 14--16, and 24 plus the bridge-qubit and
  Gidney-adder discussion audited for `T-20260824-001`

## Source-reported claims

- **LITERATURE:** Figure 10 introduces a Bell pair whose first half replaces an
  input to a concurrently executed logical operation. A destructive Bell-basis
  measurement between the stored half and the producer output completes the
  teleportation after both operations execute.
- **LITERATURE:** This bridge is described as teleporting the producer output
  "back in time". The project represents it as an acyclic prepare/use/measure/
  rebind dependency contract, not as a reverse-time graph edge.
- **LITERATURE:** Figure 16 partitions an `n`-bit Gidney adder into a first
  segment, `n-2` repeated segments, and a last segment. A repeated segment
  destroys input carry `c_j` and generates a distinct carry `c_{j+1}`.
- **LITERATURE:** The source reports `n-1` CCZ-state consumptions, active volume
  `(n-1)(22+C_CCZ)-3`, and reaction depth `2n-3` for its sequential
  active-volume Gidney adder.
- **LITERATURE:** Figure 24 gives lower active volumes for the first and last
  segments, `15+C_CCZ` and `4`, respectively.
- **LITERATURE:** Figure 14 consumes one |CCZ⟩ state with three
  two-body measurements. Their outcomes select three conditional `CZ`
  corrections, while those outcomes together with the resource single-qubit
  measurement outcomes determine Pauli corrections. The figure supplies a
  circuit-level semantic reference but not a finite qLDPC high-rate schedule.

## Derived project relevance

- **NUMERICAL:** `T-20260824-001` uses the generic bridge lifecycle as an
  independently replayed carrier-ownership contract.
- **CHECK:** Active-volume blocks and reaction depth are not J300 syndrome
  rounds or HGP logical cycles. They are not imported as executable durations.
- **CHECK:** A split XX/ZZ sensitivity schedule is an architecture adapter, not
  a claim that the surface-code active-volume implementation or Xu HGP gadget
  uses the same finite-time backend.

## Open interpretation questions

- **OPEN:** What finite HGP preparation and transversal Bell-measurement times
  apply to the exact code family selected for an ECDLP-scale implementation?
- **OPEN:** How should bridge routing range and quickswap constraints be mapped
  to a memory--processor qLDPC architecture without double-counting I/O?
