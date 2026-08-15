# Adaptive PBC/CQLU lowering contract

Task: `T-20260815-004`  
Experiment: `E-20260815-002`  
Input: `ecdlp-ftqc/phase-exact-logical-trace`, version 1  
Output: `ecdlp-ftqc/adaptive-pauli-measurement-trace`, version 1

## Scope and claim boundary

This cycle lowers the processor-resident Gidney Clifford+T trace to explicit
state preparations, Pauli-product measurements, adaptive classical controls,
Pauli-frame updates, carrier releases, and logical-value rebindings. It
preserves a live quantum output; it does not use the classical-output-only
compression guarantee of Pauli-based computation as if it were a subroutine
channel.

The trace is semantic. Every native duration remains `CHECK`. Consequently,
the result supports operation counting, Pauli-support inspection, ancilla
accounting, and a necessary processor-slot check, but not a strict Mitten
runtime.

## Source-pinned identities

- **LITERATURE:** Xu et al., arXiv:2407.18490v1, Figure 11(c), implements a
  CNOT with a `|+>` scratch, measurements `ZZ(control,scratch)`,
  `XX(scratch,target)`, and `Z(scratch)`, followed by
  `Z_control^b X_target^(a xor c)`.
- **LITERATURE:** Bravyi, Smith, and Smolin, arXiv:1506.01396v1, Figure 4,
  implements T injection with a `|T>` ancilla, `ZZ(data,magic)`, and
  `X(magic)`. The correction includes an outcome-dependent S.
- **LITERATURE:** One-bit teleportation measures
  `Z(input) tensor (U Z U^dagger)(output)` and then `X(input)` after preparing
  `U|+>`; for Clifford U the corrections remain Pauli.
- **NUMERICAL:** The implementation composes the T gadget with an adaptive
  one-bit I/S or I/S-dagger teleport. This physically removes the residual S
  frame and leaves only explicit Pauli-frame updates.

The last composition is not assigned `PROVED`: the branchwise channel test is
numerical, although it covers every nonzero measurement branch for the fixed
and seeded input states.

## Emitted gadgets

### CNOT

One reusable compiler carrier is prepared in `|+>`. The emitted measurements
are `ZZ`, `XX`, and `Z`. Three measurement bits feed the two Pauli-frame
updates. The scratch lifetime ends only after its destructive Z measurement
and frame dependency have been recorded.

### H and S

H prepares `H|+> = |0>` and measures `ZX` followed by input X. S prepares
`S|+> = |i>` and measures `ZZ` followed by input X. Both teleport the logical
value to the prepared carrier, record the conjugated Pauli corrections, and
then rebind the source logical value to the output carrier.

### T and T-dagger

Both first consume one `|T>` resource state and measure magic `ZZ` then magic
X. A second carrier is allocated only after the measured magic carrier is
released:

- T chooses `|+>` or `|i>` from the magic-ZZ outcome, implementing adaptive
  I or S teleportation;
- T-dagger chooses `|-i>` or `|+>`, implementing adaptive S-dagger or I
  teleportation.

The second stage measures `ZZ` and input X, then records Pauli-only
corrections. Magic and correction carriers do not overlap, so a serialized
operation zone can reuse one compiler scratch slot.

### Gidney erase

The source X measurement and its conditional CZ-frame dependency remain
explicit. The CZ frame has not yet been compiled to native Mitten operations;
its runtime and propagation contract remain `CHECK`.

## Generated identities

For adder width `n`, the generated adaptive trace has:

| Quantity | Count |
|---|---:|
| PBC operations | `113n - 131` |
| Pauli measurements | `53n - 62` |
| compiler-ancilla lifetimes | `20n - 23` |
| T-state demand | `4n - 4` |
| source peak logical occupancy | `n + 1` |
| minimum serialized occupancy with one scratch | `n + 2` |

These are `NUMERICAL` generated-trace identities, regression-tested for
widths 2--4 and regenerated for widths 16, 32, 58, and 59.

## Channel verification

With random seed `20260815`, the test covers 11 two-qubit inputs for CNOT and
10 one-qubit inputs for each of H, S, T, and T-dagger. Every nonzero branch is
checked after its recorded correction. The maximum Frobenius-norm density
matrix error is `9.59372693274921e-16` (`NUMERICAL`).

## Capacity refinement

The earlier width-59 result counted source-resident values only. This
compilation needs one reusable logical scratch while a gadget runs. For a
60-logical J300 block:

- width 58: source peak 59 plus scratch 1 equals 60;
- width 59: source peak 60 plus scratch 1 equals 61.

Thus width 58 is the largest tested width passing this serialized slot-count
condition. This is a necessary occupancy result, not a realizable schedule or
runtime claim. Parallel gadgets can require additional simultaneous scratch
carriers unless a one-slot operation zone serializes them.

## Strict-runtime blockers

The exact trace exposes rather than hides the remaining blockers:

1. logical `|T>` injection/preparation time and space;
2. stabilizer-state preparation time and space;
3. adaptive-preparation, decoder, and Pauli-frame reaction latency;
4. source-pinned J300 durations for Z, ZZ, and ZX measurements;
5. conditional CZ-frame propagation or execution;
6. an adaptive resource-constrained scheduler for this trace.

No provisional duration from the previous backend is promoted to a strict
result. Factory supply remains ideal and only T-state demand is retained.

## Reproduction

Run `uv --native-tls run python scripts/run_pbc_gidney_cycle.py`. The compact
summary, width-2 audit trace, branchwise verification, and environment record
are written under `experiments/runs/T-20260815-004/`.
