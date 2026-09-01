# Gidney and Fowler 2019: AutoCCZ states

- Task: `T-20260901-001`
- Source: <https://arxiv.org/abs/1905.08916v1>
- Version: arXiv:1905.08916v1, submitted 2019-05-22
- Local PDF: `literature/papers/1905.08916v1.pdf`
- Official assets: `1905.08916v1-ccz-factory.skp`,
  `1905.08916v1-ccz-fixup.skp`
- Reading status: Figures 3--6 and the factory-rate/reaction discussion audited
  directly; figure pages visually inspected at 600 DPI

## Source-reported claims

- **LITERATURE:** An AutoCCZ augments a CCZ state with three delayed-choice CZ
  correction cells. Each cell uses two routing qubits, for six total.
- **LITERATURE:** The factory output, fixup-box construction, hallway routing,
  and Toffoli consumer appear in one surface-code lattice-surgery layout.
- **LITERATURE:** In the illustrative `p=10^-3`, one-microsecond-cycle,
  ten-microsecond-reaction model, `d1=17`, `d2=27`, and six level-1 factories
  give a level-2-limited output near 7.4 kHz per factory; fourteen factories
  meet 100 kHz average demand and occupy approximately 2.6 million physical
  qubits.

## Project interpretation

- **NUMERICAL:** Direct arithmetic gives 135 cycles per output,
  `7407.407407407407 Hz`, and fourteen factories for the average demand.
- **LITERATURE:** The depicted adapter closes resource-type and local-routing
  compatibility between this source's factory and consumer.
- **OPEN:** The paper does not provide a finite decoder-throughput guarantee,
  output-buffer contract, stored-AutoCCZ error law, general delivery bound, or
  integrated consumer/factory/transport failure budget.
- **CHECK:** The cycle and reaction times are illustrative assumptions, not
  measured controller performance.

## Model mapping

- `configs/architectures/autoccz_surface_code_adapter_v1.yaml`
- `docs/AUTOCCZ_SURFACE_CODE_ADAPTER.md`
- `experiments/runs/T-20260901-001/`
