# Parallel low-rate surgery inputs (T-20260926-001)

- LITERATURE: Guo **Zhang** and Ying Li, Time-Efficient Logical Operations on
  Quantum Low-Density Parity Check Codes, arXiv:2408.01339v3 (2025-03-12),
  https://arxiv.org/html/2408.01339v3 . Appendix I.2 regularizes arbitrary
  commuting generating sets; appendix I.1 gives measurement gadgets.
- LITERATURE: Alexander Cowtan, Zhiyang He, Dominic Williamson, Theodore Yoder,
  Parallel Logical Measurements via Quantum Code Surgery, arXiv:2503.05003v3
  (2026-01-22), https://arxiv.org/html/2503.05003v3 . Sections 1.2/1.3 and 3.6
  distinguish logically disjoint, QWC, and general commuting collections.
- LITERATURE: QWC can share logical support. General commuting collections
  require generator changes and auxiliary operations, not merely a commutator
  test. Two/four primary measurement stages exclude preparation/final readout.
- OPEN: finite constants, calibrated service, physical layout, routing,
  decoding, noise/failure and state supply. This task uses capacity/timing
  parameters; it does not reproduce a finite physical backend from either paper.
- CHECK: our explicit signed symmetric-bilinear congruence implementation is a
  separately verified algorithmic realization, not a literal transcription of
  an author-provided implementation. Versioned HTML was consulted 2026-09-26.
- CHECK: T-20260926-002 pins both versioned PDFs with byte counts, PDF magic
  checks and SHA-256 in `literature/papers/INDEX.md`. The break-even generator
  requires those exact PDFs, resolving RV-20260926-001 F4.1 without changing
  the prior paper interpretation or claiming a calibrated physical backend.
