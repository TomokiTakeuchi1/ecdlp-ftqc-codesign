# Conditional Gidney-to-Mitten lowering contract

Task: `T-20260815-002`  
Experiment: `E-20260815-001`  
Logical trace: `ecdlp-ftqc/phase-exact-logical-trace`, version 1  
Backend configuration: `code-mitten-j300-k60-d14-v1`

## Scope

This bounded research cycle connects the accepted Gidney semantic DAG to a
single `[[300,60,14]]` Mitten processor block. It deliberately excludes
Memory I/O, an LP-Mitten bridge, a factory implementation, routing, atom
reservoirs, reload/spare regions, and the full ECDLP circuit.

The implementation has two separate layers:

1. a phase-exact Clifford+T trace inherited from the verified Gidney Figure 3
   channel;
2. an evidence-qualified Mitten scheduler that accepts source-supported PPM
   gadgets and rejects unresolved native lowering in strict mode.

This separation prevents a logical gate name or an accounting coefficient
from being treated as a physical Mitten gadget.

## Phase-exact Figure 3 expansion

Each temporary logical-AND compute is expanded in the exact order

1. `CNOT(x,a)`, `CNOT(y,a)`;
2. `CNOT(a,x)`, `CNOT(a,y)`;
3. parallel `T_dagger(x)`, `T_dagger(y)`, and `T(a)`;
4. `CNOT(a,x)`, `CNOT(a,y)`;
5. `H(a)`, `S(a)`.

This exact gate sequence and phase convention (`ω = exp(iπ/4)` on the
controls' `T_dagger` and the ancilla's `T`, `1j` on the final `S`) is not an
independent transcription of the paper alone: `RV-20260815-004` and
`RV-20260815-006` cross-checked it gate-for-gate against
`runtime_metadata_benchmark.gidney.coherent._apply_figure3_compute`, the
function `verify_coherent_adder` exhaustively regression-tests (all branches,
all computational-basis inputs, common-Kraus-scale phase check) to produce
the `exhaustive_small_width_coherent_regression` status this contract's
`NUMERICAL` widths 2-4 rely on. The two implementations matched exactly, so
the `NUMERICAL` label on this section's primitive counts is backed by that
verified source function, not merely inherited by convention from the parent
DAG node's evidence status.

The temporary is initially prepared in `|T>`. Its later erase remains an
X-basis measurement followed by the measurement-conditioned CZ frame update
already exposed in the source DAG. For width `n`, the resulting trace has:

| Primitive | Count |
|---|---:|
| `PREPARE_T` | `n-1` |
| `CNOT` | `12n-15` |
| `T` or `T_DAGGER` | `3n-3` |
| `H` | `n-1` |
| `S` | `n-1` |
| X measurement | `n-1` |
| conditional CZ frame update | `n-1` |
| release | `n-1` |
| all primitives | `21n-24` |
| T-state demand | `4n-4` |

These are `NUMERICAL` generated-trace identities backed by the source's
small-width phase verification and paper-general construction. They are not
Mitten runtime claims.

## Audited Mitten facts

The local primary source is Bhardwaj et al., arXiv:2607.28795v1.

- **LITERATURE:** The selected code has 300 data qubits, 60 logical qubits,
  and distance 14 (Table I).
- **LITERATURE:** The J300 single-X seed gadget adds 43 gadget qubits and
  22 X plus 22 Z checks (Table II). Figure 2 uses 11 merged-code syndrome
  rounds for the simulated single-X experiment.
- **LITERATURE:** The J300 XX seed gadget adds 100 gadget qubits and 44 X plus
  57 Z checks (Table II). Figure 2 uses 13 merged-code rounds for the simulated
  XX experiment.
- **LITERATURE:** The explicitly simulated high-rate gadget measures ten
  disjoint XX products in 13 merged-code rounds. It adds 601 gadget qubits and
  318 X plus 293 Z checks (Figure 2 and Table III).
- **LITERATURE:** The J300 full extractor adds 780 gadget qubits and 382 X
  plus 372 Z checks (Table IV).
- **CHECK:** Table IV does not report a full-extractor duration. Configuration
  v1 uses 14 rounds only as a sensitivity parameter.
- **CHECK:** A one-check-ancilla-per-stabilizer instantiation gives 240 bare
  syndrome ancillas and a 540-qubit known base footprint. This is an
  architecture configuration, not the paper's complete device footprint.

The reported rounds count repeated merged-code syndrome extraction. Setup,
final readout, decoder-tail latency, reconfiguration, and atom movement are
not silently folded into those numbers.

## High-rate eligibility

Configuration v1 greedily selects high-rate surgery only when ten ready XX
measurements have pairwise-disjoint logical support. This is the exact batch
directly simulated in the source. Nine XX measurements fall back to nine seed
surgeries. Single-X erasures are not promoted to an unverified parallel
single-Pauli gadget.

The current Gidney trace therefore uses zero high-rate operations: its
directly exposed measurements are individual X measurements. A future
Pauli-based CQLU compiler may expose parallel XX layers, but those supports
must be generated phase-exactly before high-rate eligibility is reassessed.

## Strict and provisional modes

Strict mode rejects the current full trace because phase-exact CNOT, H, S,
T/T-dagger, T preparation, conditional-frame reaction, and release have not
yet been compiled to source-audited intra-block Mitten instructions.
In particular, an intra-block CNOT is not labeled transversal: the source's
transversal-CNOT statement applies between separate CSS code blocks.

Provisional mode assigns the unresolved quantum primitives one distance-sized
14-round operation-zone slot, a conditional frame update one round, and
release zero rounds. All such events carry `CHECK`. Their unknown physical
ancilla cost is recorded as zero, so the reported physical-qubit number is
only a known lower bound and never a complete total.

## Numerical output

The deterministic provisional run gives:

| Width | Source peak occupancy | Logical primitives | Dependency-only CP | Bounded schedule | T-state demand | High-rate primitives |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 3 | 18 | 180 | 222 | 4 | 0 |
| 3 | 4 | 39 | 388 | 486 | 8 | 0 |
| 4 | 5 | 60 | 596 | 750 | 12 | 0 |
| 16 | 17 | 312 | 3,092 | 3,918 | 60 | 0 |
| 32 | 33 | 648 | 6,420 | 8,142 | 124 | 0 |
| 59 | 60 | 1,215 | 12,036 | 15,270 | 232 | 0 |

All runtime rows are `CHECK`, because they use unresolved operation costs.
The single operation-zone baseline serializes the bounded schedule, so its
runtime equals the sequential sum. The dependency-only column retains the
logical DAG lower bound under the same provisional durations.

Width 59 is the largest circuit whose *source-recorded resident values* fit
the 60-logical block; width 60 requires 61 and is `INFEASIBLE` under that
check. This is not yet an executable CQLU capacity result: any additional
logical ancilla required by the PBC compilation can reduce the maximum width.

`T-20260815-004` has now realized that warning for one explicit compilation:
the quantum-output-preserving adaptive PBC trace needs one reusable compiler
scratch, so width 58 passes the serialized 60-slot check and width 59 does
not. See `docs/PBC_CQLU_LOWERING_CONTRACT.md`. The provisional round counts
above remain historical sensitivity results and are not updated into strict
runtimes.

The known physical-qubit lower bound is 627 during single-X surgery:
540 configured base qubits plus 87 added gadget/check ancillas. It excludes
unknown CQLU gadget space and all out-of-scope architecture zones.

## Next scientific action

Use the explicit adaptive PBC trace from `T-20260815-004` to source and encode
the remaining J300 Z/ZZ/ZX, state-preparation, reaction, and conditional-CZ
costs. Then implement resource-constrained scheduling and reassess high-rate
XX batching. Until those costs are pinned, no strict runtime or complete
physical-qubit total can be reported.
