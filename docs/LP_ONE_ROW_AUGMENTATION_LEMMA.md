# One row augmentation in split canonical LP codes

- Task: T-20261008-001; owner: codex; date: 2026-10-08.
- Status: DONE; RV-20261008-001 APPROVED by claude, 2026-10-08.
- Evidence: PROVED under the explicit hypotheses below; cross-review APPROVED.

Adding the information-coordinate check \(u_1+u_2=0\) replaces two
classical kernel generators by their sum. The induced LP homology map sends
the corresponding new Z logical to the product of the two old Z logicals.
All other information generators survive. This is one algebraic lemma,
not a selective-measurement or fault-tolerance theorem.

## Hypotheses and conventions

CHECK (scope): let \(R=\mathbb F_2[x]/(x^\ell-1)\), with odd \(\ell\).
Use column vectors, \(\otimes=\otimes_R\), and
\(M^*=\overline M^{\mathsf T}\), where \(\overline x=x^{-1}\).
Binary expansion turns \(*\) into ordinary binary transpose.
Assume explicit coordinate splits

\[
A=[U\ V]\in R^{a\times(r+a)},\qquad
B^*=[W\ T]\in R^{b\times(s+b)},\qquad
V\in GL_a(R),\ T\in GL_b(R),\quad r\ge2, s\ge1.
\tag{1}
\]

The first \(r\) and \(s\) coordinates are information coordinates.
These unit-minor assumptions make A split surjective and B split injective;
they are stronger than being canonical, or merely having componentwise
full rank. Rank-dropping canonical LP examples are not covered. No
symmetry condition \(B=A^*\) is required.

Define \(g_i=(e_i,V^{-1}Ue_i)\),
\(v_j=(e_j,T^{-1}We_j)\), and \(q_j=(e_j,0)\).
Then \(g_i\) is a basis of \(\ker A\), \(v_j\) is a basis of
\(\ker B^*\), and \([q_j]\) is a basis of \(\operatorname{coker}B\).
Here each \(e_i\) has the dimension fixed by its displayed block.

LITERATURE: use Han Zheng et al.'s Z-homology convention
\(H_X=\mathbb B(d_1)\), \(H_Z^{\mathsf T}=\mathbb B(d_2)\), with

\[
C_2=R^{r+a}\otimes R^b,\quad
C_1=(R^{r+a}\otimes R^{s+b})\oplus(R^a\otimes R^b),\quad
C_0=R^a\otimes R^{s+b},
\]
\[
d_2=\begin{pmatrix}I\otimes B\\ A\otimes I\end{pmatrix},\qquad
d_1=(A\otimes I,\ I\otimes B).
\tag{2}
\]

## Lemma and proof

PROVED (conditional): set \(h=(1,1,0,\ldots,0)\) on the information
coordinates, zero on the parity coordinates, and let
\(A'=\begin{pmatrix}A\\h\end{pmatrix}\).
Write \(Q=\mathrm{LP}_\ell(A,B)\), \(Q'=\mathrm{LP}_\ell(A',B)\),
and label the merged generator by \(\mu\).

**Classical kernel.** Every vector in \(\ker A\) has the unique form
\(\sum_i u_i g_i\). The added equation is exactly \(u_1=u_2\); hence

\[
\ker A'=R(g_1+g_2)\oplus\bigoplus_{i=3}^{r}Rg_i.
\tag{3}
\]

There is no rank argument over a field hidden here. For any target
\((y,t)\in R^a\oplus R\), choose information coordinates \(u=te_1\)
and parity coordinates \(V^{-1}(y+Uu)\); their image under A' is
\((y,t)\). Thus A' is split surjective. Its parity minor on the old
parity coordinates followed by coordinate 2 is
\(\begin{pmatrix}V&Ue_2\\0&1\end{pmatrix}\), which is invertible.
The new information coordinates can be chosen as \(1,3,\ldots,r\).

**Induced LP map.** Let \(p=(I_a\ 0):R^{a+1}\to R^a\).
Since \(pA'=A\), the following maps from the primed chain to the old chain
satisfy \(d_1\gamma_1=\gamma_0d'_1\) and
\(\gamma_1d'_2=d_2\gamma_2\) by direct substitution in (2):

\[
\gamma_2=I,\qquad
\gamma_1=\operatorname{diag}(I,\ p\otimes I_b),\qquad
\gamma_0=p\otimes I_{s+b}.
\tag{4}
\]

In particular, \(\gamma_1\) keeps the first physical block and projects
out only the added part of the second block. This projection is a map of
chain modules, not a physical discard operation.

The splits in (1) decompose A into its free kernel in degree 1 plus an
invertible two-term complex, and B into its free cokernel in degree 0 plus
an invertible two-term complex. The invertible complexes are contractible,
also after tensoring. Consequently
\(H_1(Q)=\ker A\otimes\operatorname{coker}B\), and the same statement
holds for A'. There is no residual logical sector under these hypotheses.
Equation (4) induces the kernel inclusion tensored with the identity.
Using \(z_{i,j,m}=x^m(g_i\otimes q_j,0)\) as Z representatives gives

\[
\gamma_Z(\bar Z'_{\mu,j,m})=\bar Z_{1,j,m}\bar Z_{2,j,m},\qquad
\gamma_Z(\bar Z'_{i,j,m})=\bar Z_{i,j,m}\quad(i\ge3).
\tag{5}
\]

These identities hold for every \(1\le j\le s\) and
\(0\le m<\ell\). The logical counts are \(k=rs\ell\) and
\(k'=(r-1)s\ell\); this is not a single-lift-position selection.

**Dual X action.** Take old X representatives
\(x_{i,j,m}=x^m(e_i\otimes v_j,0)\), where now \(e_i\in R^{r+a}\).
Their binary pairing with the Z representatives is
\(\delta_{ii'}\delta_{jj'}\delta_{mm'}\): their supports intersect
only at the information-coordinate intersection.
The cohomology map goes in the opposite direction and is induced by
\(\gamma_1^*\), not by \(\gamma_1\).
Choose \(x'_{\mu,j,m}=x^m(e_1\otimes v_j,0)\). The two pulled-back
representatives agree modulo an X stabilizer, explicitly

\[
\gamma_1^*x_{1,j,m}+\gamma_1^*x_{2,j,m}
=d_1'^*\bigl(x^m e_{\mathrm{new}}\otimes v_j\bigr),
\tag{6}
\]

because \(A'^*e_{\mathrm{new}}=h^*\) and \(B^*v_j=0\).
Thus \(\gamma_X(\bar X_{1,j,m})=\gamma_X(\bar X_{2,j,m})
=\bar X'_{\mu,j,m}\); for \(i\ge3\),
\(\gamma_X(\bar X_{i,j,m})=\bar X'_{i,j,m}\).
The old product \(\bar X_{1,j,m}\bar X_{2,j,m}\) is in the kernel of
this pullback. These are maps between logical spaces, not a unitary that
identifies two independent logical qubits. This proves the lemma.

## What remains outside this lemma

PROVED: the single added R-valued check is \(\ell\) independent binary
classical checks, not one binary check; all \(i\ge3\) logical generators
remain. Augmentation alone therefore does not remove the other logical
operators from the image. No column was punctured or shortened here.

OPEN: removing the surviving unwanted generators by information-coordinate
shortening; rank-dropping/residual sectors; a selective measurement
instrument; distances, preparation, readout, decoding, fault tolerance and
runtime. No inference about any of these follows from this lemma.

## Source anchors

LITERATURE: [Xu et al., arXiv:2407.18490v1](https://arxiv.org/html/2407.18490v1),
Proposition 8 and Algorithm 1/Theorem 9, supply the classical-augmentation
and product-chain template. [Han Zheng et al., arXiv:2607.28605v1](https://arxiv.org/html/2607.28605v1),
Definition III.1 Eq. (11), Definition III.2 Eqs. (33)-(34), and Appendix
A.24 supply the LP convention, canonical labels and augmentation definition.
The conditional proof above is written out here; no HGP distance/FT theorem
is imported. In fact, the proof uses the explicit splits rather than CRT
or oddness; odd lift is retained only as the chosen published-family scope.
