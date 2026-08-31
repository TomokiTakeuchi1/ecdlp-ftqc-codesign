# Liu et al. 2026: In-situ simultaneous magic-state injection

- Task: `T-20260831-004`
- Source: <https://arxiv.org/abs/2604.05126v1>
- Version: arXiv:2604.05126v1, submitted 2026-04-06
- Local PDF: `literature/papers/2604.05126v1.pdf`
- Reading status: abstract and Appendix D caveat on page 12 audited directly

## Source-reported claims

- **LITERATURE:** The construction injects up to `k` logical magic states
  simultaneously inside one arbitrary CSS qLDPC block using syndrome-extraction
  resources.
- **LITERATURE:** Finite simulations include four logical `|Y>` states in the
  `[[144,12,12]]` BB code and a `[[225,9,4]]` HGP case.
- **LITERATURE:** A generally nonlocal and deep state-preparation Clifford is
  not itself fault tolerant; logical implementation or Pauli-frame absorption
  is proposed as mitigation.

## Evidence limits for this project

- **CHECK:** The finite evaluated resource is `|Y>`, not `|CCZ>`.
- **CHECK:** Generality of the formalism does not provide a finite direct-CCZ
  batch timing, error, reaction, or routing contract.
- **OPEN:** No compatibility evidence joins this injection primitive to the
  Figure 14(a) direct-CCZ consumer or Cain `P=20` backend.
