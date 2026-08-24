# Draper et al. 2006: logarithmic-depth quantum carry-lookahead addition

- Tasks: `T-20260811-002`, `T-20260824-003`
- Source: <https://arxiv.org/abs/quant-ph/0406142v1>
- Version: arXiv:quant-ph/0406142v1, submitted 2004-06-20; journal publication 2006
- Local PDF: `literature/papers/quant-ph-0406142v1.pdf`
- SHA-256: `30B68CC62C73E5AA6E4D59A6C3CF3C582FB62420F8BDE420DE142506A2BB11D6`
- Reading status: Sections 3, 4.2, and 5.1, Figures 4--5, and Tables 1--2
  audited directly from the pinned PDF for `T-20260824-003`

## Admitted variant

- **LITERATURE:** The implemented circuit is the in-place adder modulo `2^n`
  with no incoming carry and no exported overflow bit. Its register contract is
  `(A,B)->(A,A+B mod 2^n)`.
- **LITERATURE:** Section 5.1 obtains the modulo circuit from Section 4.2 by
  omitting the high generate bit and running both carry circuits on `n-1`
  bits.
- **CHECK:** Controlled addition, out-of-place addition, incoming carry, and
  modulo `2^n-1` are different source variants and are not silently inferred
  from this implementation.

## Source-reported finite formulas

Let `w(x)` be Hamming weight and `floorlog(x)=floor(log2(x))`.

- **LITERATURE:** The Section-3 carry circuit of length `L` uses
  `4L-3w(L)-3floorlog(L)-1` Toffolis and
  `L-w(L)-floorlog(L)` scratch ancillas.
- **LITERATURE:** In the normal-size regime, its Toffoli depth is
  `floorlog(L)+floorlog(L/3)+3`. The paper notes that this expression
  overcounts some small cases (`L<=3`).
- **LITERATURE:** The in-place modulo adder uses
  `10n-6w(n-1)-6floorlog(n-1)-12` Toffolis, `4n-5` CNOTs,
  `2n-2` NOTs, and `2n-2-w(n-1)-floorlog(n-1)` ancillas.
- **LITERATURE:** For the stated normal sizes its complete source time-slice
  depth is
  `2floorlog(n-1)+2floorlog((n-1)/3)+14`. Table 2 uses an additional
  `n>=7` presentation restriction; the implementation does not extrapolate
  that table to tiny widths.

## Prefix-round structure

- **LITERATURE:** Section 3 defines propagate rounds `P`, generate rounds `G`,
  carry-completion rounds `C`, and inverse propagate rounds `P^-1`.
- **LITERATURE:** `P` round `t+1` may overlap `G` round `t`, and `C` round `t`
  may overlap inverse-`P` round `t+1`. Gates within a time slice still obey
  bounded fan-out: a logical wire participates in at most one gate.
- **NUMERICAL:** The generated DAG records those source overlaps explicitly
  and derives causality from the nearest prior use of each wire, rather than
  turning source-list adjacency into a dependency.

## Reproduced project results

- **NUMERICAL:** Widths 2--6 pass exhaustive reversible-gate replay for every
  pair of basis inputs, including preservation of `A`, modular output in `B`,
  and cleanup of all carry and prefix ancillas.
- **NUMERICAL:** Boundary widths through 257 reproduce the admitted gate,
  ancilla, and normal-size depth formulas.
- **NUMERICAL:** At width 256 the trace has 2,458 Toffolis, 1,019 CNOTs,
  510 NOTs, 495 source ancillas (240 reusable prefix scratch values), and 40
  source algorithmic time slices. Peak Toffoli demand is 255 in one source
  slice.
- **CHECK:** A source time slice is not an executable QEC cycle. High-rate
  surgery, processor capacity, memory I/O, routing, factories, decoding,
  reaction, and logical failure are intentionally absent.

## Open interpretation questions

- **OPEN:** Which prefix Toffolis can be compiled into source-supported
  high-rate Pauli-product families without losing the QCLA layer structure?
- **OPEN:** How much of the 255-Toffoli initial burst survives processor
  capacity, carrier/scratch, routing, operation-zone, and factory constraints?
- **OPEN:** Does QCLA's extra workspace increase memory traffic enough to erase
  its source-depth advantage over the reviewed ripple alternatives?
- **OPEN:** What controlled-QCLA construction should be admitted for elliptic-
  curve scalar multiplication?
