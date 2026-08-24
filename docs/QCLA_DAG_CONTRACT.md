# Source-pinned in-place QCLA DAG contract

Task: `T-20260824-003`  
Experiment: `E-20260824-003`  
Trace schema: `ecdlp-ftqc/qcla-inplace-mod2n-trace`, version 1

## Claim boundary

This cycle reconstructs Draper et al.'s in-place addition modulo `2^n` as an
architecture-neutral reversible gate DAG. It exposes the concurrency and
workspace that a later high-rate-surgery and memory scheduler must serve. It
does not assign QEC durations or claim executable speedup.

| Claim | Evidence | Qualification |
|---|---|---|
| The emitted gate sequence is the selected Draper source construction | `LITERATURE` | Sections 3, 4.2, and 5.1; Figures 4--5; Tables 1--2 |
| Widths 2--6 map `(A,B)` to `(A,A+B mod 2^n)` and clean every ancilla | `NUMERICAL` | Exhaustive computational-basis replay of 16, 64, 256, 1,024, and 4,096 input pairs |
| Generated counts and normal-size layer depth reproduce the source formulas | `NUMERICAL` | Widths 2--33 plus boundaries 255/256/257 are regression tested |
| The 40 width-256 source layers are executable FTQC time | `CHECK` | False at present; no code, processor, routing, memory, factory, decoder, or failure model is applied |

Because the instruction set is only X, CNOT, and Toffoli, every gate is a
phase-free basis permutation. Exhaustive basis replay at a tested width checks
the entire unitary permutation for that finite circuit, including ancilla
cleanup. It remains a finite numerical verification, not a proof for arbitrary
`n` or an independent proof of the paper.

## Pinned source and selected semantics

The source is arXiv:quant-ph/0406142v1, local PDF SHA-256
`30B68CC62C73E5AA6E4D59A6C3CF3C582FB62420F8BDE420DE142506A2BB11D6`.
The admitted variant is:

- input registers `A[0:n]` and `B[0:n]`, least-significant bit first;
- zero-initialized carry ancillas `z[1:n]` and the paper's prefix scratch;
- no incoming carry;
- no exported overflow; and
- output `(A, A+B mod 2^n)` with all ancillas returned to zero.

Out-of-place addition, controlled addition, modulo `2^n-1`, and overflow are
separate source contracts. They are not configuration flags on this trace.

## Ten-step reversible sequence

The frontend emits Section 4.2 with the Section 5.1 modulo modification:

1. compute `n-1` initial generates into `z[1:n]`;
2. compute bit propagates in `B`;
3. run the Section-3 carry circuit at length `L=n-1`;
4. XOR carries into the high `B` bits;
5. complement the low `n-1` `B` bits;
6. prepare the modified propagates for reverse carry cleanup;
7. run the exact reverse of the length-`L` carry circuit;
8. restore the modified propagates;
9. uncompute initial generates; and
10. restore the complemented output bits.

Every gate records kind, controls, target, read and written logical values,
source step, source algorithmic layer, carry direction, prefix round, prefix
index triple, and evidence label.

## Prefix rounds and source layers

For carry length `L`, the trace expands the paper's four round families:

- `P_t`: build block propagates into scratch;
- `G_t`: build block generates;
- `C_t`: distribute the required global carries to non-power-of-two positions;
- `P_t^-1`: clean prefix scratch.

The source permits `P_(t+1)` with `G_t`, and `P_(t+1)^-1` with `C_t`.
Those overlaps are retained only when all gate supports are disjoint. Trace
validation rejects two gates in the same source layer if they share even a
read-only control, preserving the source's bounded-fan-out model.

The source layer index is an admitted circuit schedule. Separately, the DAG
stores only nearest-prior-wire dependencies and reports a unit-gate dependency
critical path. It does not add an edge merely because two gates are adjacent
in the paper or generated list. At width 256 both quantities happen to be 40;
they remain separate fields because a different circuit need not make them
equal.

For `n>=5`, the generated full-circuit layer count reproduces

```text
2 floor(log2(n-1)) + 2 floor(log2((n-1)/3)) + 14.
```

The source warns that its carry-depth expression overcounts some `L<=3`
cases. The implementation emits only nonempty slices at widths 2--4, producing
6, 10, and 12 layers respectively, and does not claim that these are values
from the paper's normal-size table.

## Dependencies and independent replay

For each logical value, the DAG adds a dependency from its nearest previous
gate use to its next use. This captures target order, control reuse, bounded
fan-out, and uncomputation without confusing serialized source text with
causality. Validation reconstructs this edge set from the gate records and
rejects missing, extra, unknown, or cyclic dependencies.

`replay_qcla` initializes `A` and `B` from integers and every recorded ancilla
to zero, then evaluates only the emitted X/CNOT/Toffoli records. It independently
checks the two output registers and final ancilla state. Tests also mutate
dependencies and layer supports to confirm fail-closed validation.

The experiment checks:

- all input pairs at widths 2--6;
- 128 seeded input pairs at each of widths 7, 8, 9, 15, 16, and 17;
- count, layer, topology, and carry-cleanup boundaries at widths 32, 255, 256,
  and 257; and
- deterministic JSON serialization.

## Ancilla lifecycle

The `n-1` carry ancillas remain allocated across the reversible construction.
Each prefix scratch value has two explicit reuse epochs: compute/uncompute in
the forward carry circuit, then compute/uncompute again during the reverse
carry circuit. The trace derives interval endpoints from target occurrences,
and validation recomputes them rather than trusting cached counts.

The source ancilla formula is

```text
2n - 2 - w(n-1) - floor(log2(n-1)),
```

where `w` is Hamming weight. This is logical circuit workspace, not physical
qubits or processor-resident occupancy. A later memory model may place some
values outside the processor and must then account for every move.

## Reproduced width-256 structure

| Quantity | Value | Unit/qualification |
|---|---:|---|
| X | 510 | reversible logical gates |
| CNOT | 1,019 | reversible logical gates |
| Toffoli | 2,458 | reversible logical gates |
| Total gates | 3,987 | X+CNOT+Toffoli |
| Carry ancillas | 255 | logical circuit values |
| Prefix scratch | 240 | distinct reusable logical circuit values |
| Total source ancillas | 495 | logical circuit values, not physical qubits |
| Source layers | 40 | algorithmic time slices, not QEC cycles |
| Unit-gate DAG critical path | 40 | gates, before backend constraints |
| Peak Toffoli demand | 255 | one source layer |

The complete Toffoli time series is
`experiments/runs/T-20260824-003/qcla_width256_toffoli_demand.json`.
It is demand, not service: no assumption says a factory or operation zone can
supply or execute 255 Toffolis simultaneously.

## Reproducibility

Run:

```text
uv --native-tls run python scripts/run_qcla_cycle.py
```

The generator verifies the configured source ID, arithmetic contract, and PDF
hash before emitting:

- `experiments/runs/T-20260824-003/summary.json`;
- `experiments/runs/T-20260824-003/qcla_width8_trace.json`;
- `experiments/runs/T-20260824-003/qcla_width256_structure.json`;
- `experiments/runs/T-20260824-003/qcla_width256_toffoli_demand.json`; and
- `experiments/runs/T-20260824-003/reproducibility.json`.

The reproducibility record identifies the task, Git/worktree state, source PDF,
configuration, code bindings, random seed, environment, output path, and
validation status. Generated result files must be changed only by changing an
input or generator and rerunning it.

## Deliberately unresolved

- Toffoli-to-CCZ/T/adaptive-PBC lowering and phase/frame details;
- exact-ten or other high-rate-surgery eligibility and carrier allocation;
- processor capacity, operation throughput, routing, and inter-block links;
- processor-memory placement, prefetch, and transfer latency;
- time-dependent factory production, retry, buffer, and backlog;
- decoding, classical reaction, logical error, and total failure budget;
- controlled QCLA and its use in point addition; and
- QEC-cycle, wall-clock, spacetime-volume, or complete physical-qubit results.

The next research cycle should consume the exact gate supports and layerwise
Toffoli demand here, lower one source-pinned prefix primitive, and preserve the
distinction between source parallelism and executable architecture parallelism.
