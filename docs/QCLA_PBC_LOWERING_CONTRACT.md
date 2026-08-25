# QCLA to adaptive-PBC resident-J300 contract

Task: `T-20260825-001`  
Experiment: `E-20260825-001`  
Input: `ecdlp-ftqc/qcla-inplace-mod2n-trace`, version 1  
Intermediate: `ecdlp-ftqc/phase-exact-logical-trace`, version 1  
Output: `ecdlp-ftqc/adaptive-pauli-measurement-trace`, version 1

## Scope and claim boundary

This cycle composes the reviewed in-place modulo-`2^n` QCLA with a pinned,
ancilla-free exact CCX decomposition and the already-reviewed adaptive-PBC
gadgets. It preserves live quantum outputs and source provenance through QCLA
gate, prefix stage, direction, source layer, CCX column, and logical primitive.

The J300 schedule is a `CHECK` sensitivity calculation. It uses unresolved
preparation, measurement, extractor, and reaction costs and assumes ideal
resource-state supply without stalls. It is not a strict runtime, a physical-
qubit total, or a wall-clock estimate.

## Exact CCX baseline

- **LITERATURE:** Selinger, arXiv:1210.0974v2, circuit (1), supplies the
  selected seven-T-family CCX: six CNOTs, two H gates, one S gate, three T
  gates, and four T-dagger gates.
- **NUMERICAL:** Independent reconstruction of the full 8-by-8 unitary agrees
  with ideal CCX up to global phase with maximum error
  `2.220446049250313e-16`.
- **LITERATURE:** Circuit (1) has T-depth 6, reducible by commutation to the
  paper's circuit (2) with T-depth 4. The implementation preserves the exact
  circuit-(1) wire order and its two disjoint same-column pairs. It does not
  identify either paper depth with backend time.
- **OPEN:** Direct CCZ injection remains a separate comparator. No result here
  says the seven-T route is factory-, space-, or time-optimal.

## Logical and PBC semantics

Every QCLA X becomes a deterministic affine Pauli-frame update. The frame
expression is `1 XOR parity([])`, so no artificial H/S quantum sequence is
introduced. Every QCLA CNOT remains one logical CNOT. Every Toffoli expands to
the exact 16 primitives above. Nearest-wire dependencies are then re-derived
over expanded columns; source-list adjacency and source-layer depth are not
used as executable causality.

The reviewed PBC compiler maps the logical primitives as follows:

| Logical primitive | Adaptive representation |
|---|---|
| X | deterministic X Pauli-frame update |
| CNOT | `ZZ`, `XX`, and scratch-Z measurement gadget |
| H, S | one-bit Clifford teleportation |
| T, T-dagger | T-state injection plus adaptive Clifford teleportation |

Compiler-carrier allocation, release, rebinding, measurement outcomes, and
classical feed-forward remain explicit. T-state demand is a time-independent
count in this cycle; factory output, retry, buffer, burst service, and routing
are absent.

## Generated width-256 structure

The source has 2,458 Toffolis, 1,019 CNOTs, and 510 X gates. The admitted
expansion deterministically produces:

| Logical quantity | Count |
|---|---:|
| total primitives | 40,857 |
| CNOT | 15,767 |
| H | 4,916 |
| S | 2,458 |
| T | 7,374 |
| T-dagger | 9,832 |
| X-frame updates | 510 |
| T-state demand | 17,206 |

These are `NUMERICAL` lowering counts. A width-256 adaptive-PBC trace and
schedule are deliberately not constructed after the resident-capacity check
fails.

## Resident J300 capacity

For width `n`, necessary source occupancy is `2n + a(n)`, where `a(n)` is the
reviewed QCLA source-ancilla count. A serialized PBC execution needs at least
one compiler scratch; the supported high-rate ten-XX rule needs ten distinct
live scratch slots.

| Width | Source slots | +1 scratch | +10 scratch |
|---:|---:|---:|---:|
| 14 | 48 | 49: fits | 58: fits |
| 15 | 52 | 53: fits | 62: rejects |
| 16 | 55 | 56: fits | 65: rejects |
| 17 | 61 | 62: rejects | 71: rejects |
| 256 | 1,007 | 1,008: rejects | 1,017: rejects |

The inequalities are `PROVED` integer accounting under the fully resident
model. They are necessary conditions only. Width 256 fails closed with a
message requiring an explicit memory partition; no fictitious J300 schedule
is emitted.

## High-rate sensitivity

The existing rule selects exactly ten ready, pairwise-disjoint XX products on
ten distinct live scratch carriers. Under one provisional operation zone:

| Width | Serial, 1 scratch | High-rate, 10 scratch | Ten-XX batches |
|---:|---:|---:|---:|
| 2 | 2,151 | 2,151 | 0 |
| 4 | 10,535 | 10,535 | 0 |
| 8 | 39,219 | 39,219 | 0 |
| 11 | 69,669 | 68,850 | 7 |
| 14 | 94,161 | 93,108 | 9 |

The values are syndrome-round-shaped `CHECK` sensitivities, not strict
execution times. The nonzero width-11/14 results show that exact PBC supports
expose real eligible batches after processor and scratch constraints; they do
not show that source Toffoli layers execute wholesale or that factory and
routing constraints can sustain the bursts.

## Explicit exclusions and next boundary

- memory partitioning, load/store placement, and transfer timing;
- direct CCZ injection and T/CCZ factory supply, retry, buffers, and routing;
- decoder throughput, reaction tails, and logical failure budget;
- controlled QCLA for scalar multiplication;
- QEC-cycle duration and wall-clock conversion.

The next executable comparison must introduce a memory partition for QCLA and
jointly schedule memory traffic, PBC scratch, high-rate surgery, and a factory
service time series. Until then, width 256 remains a structural-demand result.

## Reproduction

Run `uv --native-tls run python scripts/run_qcla_pbc_cycle.py`. Generated
artifacts are written under `experiments/runs/T-20260825-001/`; the source PDF,
configuration, code bindings, working-tree state, environment, and validation
status are recorded in `reproducibility.json`.
