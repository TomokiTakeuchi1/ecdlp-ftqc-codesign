# Menon et al. 2025: Magic tricycles

- Task: `T-20260831-004`
- Source: <https://arxiv.org/abs/2508.10714v2>
- Version: arXiv:2508.10714v2, revised 2025-11-06
- Local PDF: `literature/papers/2508.10714v2.pdf`
- Reading status: abstract and pages 6, 12, and 49 audited directly

## Source-reported claims

- **LITERATURE:** Finite tricycle qLDPC blocks support constant-depth physical
  circuits with logical CCZ action across three code blocks.
- **LITERATURE:** The paper reports circuit-level simulations, finite blocks of
  roughly 50--100 qubits, and logical memory error rates down to `6e-10` with
  postselection for selected codes.
- **LITERATURE:** It provides optimal-depth syndrome-extraction circuits and a
  reference reconfigurable-neutral-atom rearrangement procedure.
- **LITERATURE:** Extracting disjoint CCZ states requires selective logical
  initialization; concrete efficient teleportation into a target computation
  code is left for future work.

## Evidence limits for this project

- **CHECK:** The reported low logical error is a memory simulation and does not
  include error introduced by the CCZ circuit when evaluating final
  magic-state fidelity.
- **CHECK:** `K_CCZ` values are extraction lower bounds and do not by themselves
  define factory throughput, delivery, or buffer service.
- **OPEN:** No finite adapter joins these states to the reviewed Figure 14(a)
  direct-CCZ consumer in the selected Cain time-efficient backend.
