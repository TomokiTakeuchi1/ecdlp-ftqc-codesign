# Z distance inheritance for the shortened LP helper

- Task: T-20261009-002; owner: codex; date: 2026-10-09.
- Status: DONE; RV-20261009-002 APPROVED by claude, 2026-10-09.
- Evidence: PROVED under the hypotheses below; cross-review approved.

Under the approved split assumptions at r=3, the augmented and shortened
helper has Z distance at least that of the original data code. The proof
uses a physical-weight inequality and an injective map on logical classes.
It does not require an ideally prepared helper and supplies no X-distance
or fault-tolerance guarantee.

## Codes and distance convention

CHECK (scope): inherit the [augmentation](LP_ONE_ROW_AUGMENTATION_LEMMA.md)
and [shortening](LP_ONE_COORDINATE_SHORTENING_LEMMA.md) hypotheses, with
\(R=\mathbb F_2[x]/(x^\ell-1)\), positive odd \(\ell\), r=3 and s>=1.
Thus \(A=[U\ V]\), \(B^*=[W\ T]\), with the common coordinate parity
minors V and T invertible over R. Let
\(Q=\mathrm{LP}_\ell(A,B)\) and \(Q_h=Q''=\mathrm{LP}_\ell(A'',B)\),
where A'' augments A by the information check u1+u2=0 and then shortens
old information coordinate 3, as in the approved lemma. The data code is
unchanged. These assumptions exclude residual and rank-dropping sectors.

Use binary check matrices \(H_X=\mathbb B(d_1)\),
\(H_Z^{\mathsf T}=\mathbb B(d_2)\), and the analogous helper matrices.
For either code define Z cycles, Z stabilizers and Z logical classes by
\(\mathcal Z_Z=\ker H_X\),
\(\mathcal B_Z=\operatorname{im}H_Z^{\mathsf T}\), and
\(\mathcal L_Z=\mathcal Z_Z/\mathcal B_Z\). The distance is

\[
d_Z(Q_t)=\min_{z\in\mathcal Z_Z(Q_t)\setminus\mathcal B_Z(Q_t)}
\operatorname{wt}_{\rm bin}(z),\qquad t\in\{D,h\},\quad Q_D=Q.
\tag{1}
\]

The weight counts physical binary qubits, not nonzero ring coordinates or
logical PPM factors. The minimum includes all Z-stabilizer representatives,
not only the canonical generators. Both codes encode nonzero numbers of
qubits: \(k_D=3s\ell\) and \(k_h=s\ell\).
All weights are evaluated in the original physical coordinates. Split-basis
changes using V^{-1} or T^{-1} establish logical statements, not isometries
of this weight.

## Lemma and proof

PROVED (conditional):

\[
d_Z(Q_h)\ge d_Z(Q).
\tag{2}
\]

Write \(p=(I_a\ 0)\), and let iota insert zero at old coordinate 3.
The approved chain map gives the binary physical map

\[
F=\mathbb B\left(\operatorname{diag}
(\iota\otimes I_{s+b},p\otimes I_b)\right).
\tag{3}
\]

First, F does not increase binary weight. Its ring entries are only 0 and
1, which expand to zero blocks and identity matrices; no polynomial entry
spreads one binary position over several positions. Split an arbitrary
helper vector as \(z=(u,v_{\rm old},v_{\rm new})\), where u is the first
physical block and v_new comprises the second-block coordinates associated
with the added check. The first block of F inserts zeros, and the second
keeps v_old and drops v_new. Their output supports are disjoint, so

\[
\operatorname{wt}_{\rm bin}(Fz)
=\operatorname{wt}_{\rm bin}(u)+\operatorname{wt}_{\rm bin}(v_{\rm old})
=\operatorname{wt}_{\rm bin}(z)-\operatorname{wt}_{\rm bin}(v_{\rm new})
\le\operatorname{wt}_{\rm bin}(z).
\tag{4}
\]

F has zero columns on the added-check part when that block is nonempty;
neither physical injectivity nor weight equality on every vector is claimed.

Second, the chain-map squares send helper Z cycles to data Z cycles and
helper Z stabilizers to data Z stabilizers. Hence F induces
\(F_*:\mathcal L_Z(Q_h)\to\mathcal L_Z(Q)\). The approved complete
logical map at r=3 is

\[
F_*[z_{h,j,m}]=[z_{1,j,m}]+[z_{2,j,m}],\qquad
1\le j\le s,\quad 0\le m<\ell.
\tag{5}
\]

The helper classes on the left form its whole binary logical Z basis;
there is no residual sector. A nonzero binary combination of the images
has the same nonzero coefficient vector in the first data logical family,
so it cannot vanish in the independent canonical data basis. Thus F_* is
injective on logical classes, even though F need not be injective physically.

Now take any \(z\in\mathcal Z_Z(Q_h)\setminus\mathcal B_Z(Q_h)\).
The chain squares make Fz a data cycle; injectivity makes its class nonzero,
so Fz is not a data stabilizer. This holds after adding any helper Z
stabilizer, including representatives with support in both physical blocks.
By (1) and (4),

\[
d_Z(Q)\le\operatorname{wt}_{\rm bin}(Fz)
\le\operatorname{wt}_{\rm bin}(z).
\tag{6}
\]

Minimizing over all such helper z proves (2).

## Scope and relation to fault tolerance

PROVED: this is a relative, one-sided code-distance bound. It supplies no
numerical distance unless the data distance is independently known. It is
a property of the two codes and their map; it does not use the ideal-state
or noiseless-circuit assumptions of the measurement lemma (A-0071).

OPEN: an X-distance lower bound, the full CSS distance, protection of Z
readout outcomes against X-type faults, noisy preparation, decoding and
circuit-level fault tolerance. The existing X pullback has a different
direction and a nontrivial kernel, so the proof above is not an X-distance
proof by relabeling. No general-r or residual-sector extension is asserted.

LITERATURE: [Xu et al., arXiv:2407.18490v1, Theorem 9](https://arxiv.org/html/2407.18490v1)
uses preservation of a classical distance and a full-rank HGP distance
formula to support its FT construction. That HGP formula is not assumed
for LP here. Equations (2)-(6) follow directly from the approved LP map and
the physical binary-weight definition.
