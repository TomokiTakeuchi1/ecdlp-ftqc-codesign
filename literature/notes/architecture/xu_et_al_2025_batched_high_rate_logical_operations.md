# Xu et al. 2025: Batched high-rate logical operations

- Task: `T-20260831-004`
- Source: <https://arxiv.org/abs/2510.06159v1>
- Version: arXiv:2510.06159v1, submitted 2025-10-07
- Local PDF: `literature/papers/2510.06159v1.pdf`
- Reading status: abstract and finite non-Clifford construction on page 7 audited directly

## Source-reported claims

- **LITERATURE:** Batched gadgets apply the same logical operation across many
  CSS qLDPC blocks with constant asymptotic space-time overhead under a
  fast-classical-computation assumption.
- **LITERATURE:** The framework includes global T and CCZ constructions via
  code switching or high-rate distillation in the general development.
- **LITERATURE:** The finite self-dual BB proposal emphasizes global T gates
  supplied by parallel magic-state cultivation.

## Evidence limits for this project

- **CHECK:** The finite BB construction is not a finite Figure 14(a)
  direct-CCZ consumer with decoded reaction, port, routing, and delivery values.
- **CHECK:** “Fast classical computation” cannot substitute for measured
  decoder throughput or a bounded feed-forward latency.
- **OPEN:** An explicit adapter would be required before importing these
  high-rate operations into the selected Cain direct-CCZ backend.
