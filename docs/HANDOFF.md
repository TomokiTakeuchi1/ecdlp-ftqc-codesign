# Handoff: the ECDLP-256 architecture decision space

## Mission

Our working objective is to identify an FTQC architecture
that could execute a full ECDLP-256 Shor computation in **at most one week**
with a physical-qubit footprint on the order of **\(10^4\)**. This is a design
target, not a reproduced resource estimate. The canonical full ECDLP circuit,
finite backend schedule, factory service model, and end-to-end failure budget
are not yet closed.

Point addition is the working arithmetic hotspot in the ECDLP workload.
Consequently, the near-term
co-design question is: *which architecture can realize elliptic-curve point
addition most efficiently once logical-operation, reaction, factory, routing,
memory, and decoding constraints are all counted?* A point-addition circuit is
not yet a proxy for the full algorithm; it is the most useful place to expose
the relevant bottlenecks first.

## From point addition to full Shor

The complete ECDLP version of Shor's algorithm uses quantum registers to
control a sequence of elliptic-curve point additions by known points. Those
controlled additions implement the group action whose periodic structure is
then extracted by quantum Fourier sampling and classical post-processing. In
that sense, an efficient point-addition circuit is a central building block,
but not the whole computation: the full workload also includes control,
register management, Fourier sampling, and repeated use of the arithmetic.

[André Schrottenloher, *Optimized Point Addition Circuits for Elliptic Curve
Discrete Logarithms* (2026)](https://arxiv.org/abs/2606.02235) is the key
entry point for this bridge from the arithmetic primitive to the full ECDLP
Shor workload. It provides the point-addition circuit perspective that the
architecture comparison needs to support.

## Two competing architecture tracks

### 1. Teleportation-based ripple carry + HGP/RASCqL (the “Rascal” working design)

This track starts from a teleportation-based ripple-carry adder and an
HGP-style logical-operation set. Its central idea is to arrange the operations
so that each *online* classical dependency has a bounded, ideally constant,
reaction-time cost. Classical feed-forward is shifted as far as possible into
offline preparation of GHZ-type entanglement and magic/resource states; the
code and preparation scheme must make that offline work efficient as well.

Gidney's ripple-carry adder is the arithmetic starting point. The RASCqL
paper is the key architecture reference for the “Rascal” part of the design:
it studies application-tailored qLDPC logic units under a reaction-time
constraint, which is the same systems question this track must answer for
point addition.

Why it is promising:

- HGP constructions support highly parallel logical PPMs, and the segmented
  teleportation construction exposes parallel segment work.
- Teleportation can move a carry dependency into an explicit prepare/use/
  measure/rebind lifecycle rather than forcing all work to be serial.

What remains uncertain:

- finite code-distance scaling and logical-error behavior for the chosen HGP
  construction;
- preparation time, success probability, footprint, buffering, and routing for
  the offline GHZ and magic-state supply; and
- the fact that, although segment work can be parallel, the
  reactive-measurement tail is not automatically parallel. Algorithmic
  parallelism must not be relabeled as wall-clock speedup.

### 2. Carry-lookahead adder (QCLA) + high-rate surgery

QCLA exposes much more source-level parallelism than ripple carry. For 256
bits, the clean out-of-place QCLA has 20 source CCX layers; the in-place
version has 40. Thus, an idealized model in which each admissible QCLA layer
costs roughly \(O(d)\) syndrome rounds can look substantially better than the
ripple track. This is why QCLA plus a high-rate qLDPC processor is a leading
candidate.

The important qualification is that *20 or 40 source layers are not physical
time*. The attractive idealized estimate only survives if the architecture can
actually support each layer's measurement supports, correction collection,
ports, and resource-state burst.

The main evaluation questions are:

- Should QCLA be partitioned into processor-sized subcircuits, or can enough
  of its prefix network remain resident to preserve its advantage?
- Can a high-rate code realize the required topology of up to 255 source-level
  parallel CCXs/CCZ consumptions without conflicting supports, extractor
  limits, or routing congestion?
- How are outcomes from injection/gate teleportation collected, decoded, and
  turned into the required conditional corrections within a layer?
- Can magic factories, delivery paths, and a finite buffer serve the *time
  series* of CCZ/T demand, including bursts, rather than merely its average
  rate?

The current finite high-rate evidence is encouraging but narrower: the
reviewed J300 mitten-code result demonstrates a 10-disjoint-XX high-rate
gadget in 13 merged-code syndrome rounds. It does **not** yet admit arbitrary
255-way parallel direct-CCZ injection, a complete QCLA layer, or a factory-to-
consumer schedule.

## Concepts and recommended entry points

| Concept | Why it matters here | First reference |
|---|---|---|
| ECDLP point addition | Connects the optimized arithmetic primitive to controlled group operations in the complete ECDLP Shor computation. | [Schrottenloher, *Optimized Point Addition Circuits for Elliptic Curve Discrete Logarithms* (2026)](https://arxiv.org/abs/2606.02235) |
| Ripple-carry addition | The baseline arithmetic construction for the teleportation-ripple track. | [Gidney, *Halving the Cost of Quantum Addition* (2018)](https://arxiv.org/abs/1709.06648) |
| RASCqL | An application-tailored qLDPC complex-logic architecture that foregrounds reaction-time constraints. | [Yang *et al.*, *Spacetime-Efficient and Hardware-Compatible Complex Quantum Logic Units in qLDPC Codes* (2026)](https://arxiv.org/abs/2602.14273) |
| Cultivation | Offline high-fidelity magic-state preparation may be the mechanism that absorbs feed-forward work. Its yield, time, and layout belong in the resource model. | [Sahay *et al.*, *Fold-transversal surface code cultivation* (2025)](https://arxiv.org/abs/2509.05212) |
| Pauli-based computation (PBC) | Describes computation through measurements, resource states, and a classical correction frame—the right vocabulary for tracking online dependencies. | [Litinski, *A Game of Surface Codes* (2019)](https://arxiv.org/abs/1808.02892) |
| Teleportation ripple carry and HGP operations | Supplies the bridge-carry/HGP comparison route: parallel PPMs, GHZ/magic primitives, and a segmented adder with an explicit reactive tail. | [Xu *et al.*, *Fast and Parallelizable Logical Computation with Homological Product Codes* (2024)](https://arxiv.org/abs/2407.18490) and [Litinski & Nickerson, *Active Volume* (2022)](https://arxiv.org/abs/2211.15465) |
| Carry lookahead (QCLA) | Provides logarithmic source depth and makes the peak prefix-layer concurrency explicit. | [Draper *et al.*, *A Logarithmic-Depth Quantum Carry-Lookahead Adder* (2006)](https://arxiv.org/abs/quant-ph/0406142) |
| High-rate surgery | Provides a general framework for many addressable logical PPMs in parallel using a shared ancilla system. | [Zheng, Jiang & Xu, *High-Rate Surgery: towards Constant-Overhead Logical Operations* (2025)](https://arxiv.org/abs/2510.08523) |
| High-rate processor codes | Mitten codes give a concrete high-rate-surgery and parallel-injection candidate, with finite-size experiments; these capabilities must be used only at their demonstrated scope. | [Bhardwaj *et al.*, *High-rate qLDPC Processors* (2026)](https://arxiv.org/abs/2607.28795) |
| Canonical lifted-product (LP) codes | A second high-rate-code route with a co-designed logical basis, parallel PPMs, and parallel magic-state injection. | [Zheng *et al.*, *Logical Computation with Canonical Lifted Product Codes* (2026)](https://arxiv.org/abs/2607.28605) |
| Distillation | Establishes a surface-code factory baseline and explains why factory cost cannot be reduced to a magic-state count. | [Litinski, *Magic State Distillation: Not as Costly as You Think* (2019)](https://arxiv.org/abs/1905.06903) |
| Zoned neutral-atom architecture | The closest system-level comparison: separate memory, processor, operation, and resource-state zones, plus QCLA-based time-efficient estimates. | [Cain *et al.*, *Shor's Algorithm Is Possible with as Few as 10,000 Reconfigurable Atomic Qubits* (2026)](https://arxiv.org/abs/2603.28627) |

## Current bottom line

The QCLA/high-rate-surgery route currently looks stronger in idealized timing
studies because its source dependency depth is small. The
teleportation-ripple/HGP route may win if its offline preparation and
constant-reaction operation set can be made finite, high-fidelity, and cheap.
Neither conclusion is established until the unresolved preparation, topology,
classical-control, factory, buffering, routing, decoder, and failure-budget
questions are answered with one compatible backend model.
