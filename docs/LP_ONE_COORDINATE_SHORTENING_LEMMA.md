# One information coordinate shortening in split canonical LP codes

- Task: T-20261008-011; owner: codex; date: 2026-10-08.
- Status: DONE; RV-20261008-011 APPROVED by claude, 2026-10-08.
- Evidence: PROVED under the hypotheses below; cross-review approved.

Shortening information coordinate 3 after the previous augmentation removes
the Z3 logical family from the helper's image while retaining Z1 Z2 and
the other families. The data code itself is unchanged. This is one
algebraic lemma, not a physical discard or a measurement-channel theorem.

## Setup

CHECK (scope): inherit the common unit-minor hypotheses and conventions of
[the approved augmentation lemma](LP_ONE_ROW_AUGMENTATION_LEMMA.md), with
the stronger requirement \(r\ge3\). Explicitly,
\(R=\mathbb F_2[x]/(x^\ell-1)\) with odd \(\ell\),
\(A=[U\ V]\in R^{a\times(r+a)}\),
\(B^*=[W\ T]\in R^{b\times(s+b)}\),
\(V\in GL_a(R)\), \(T\in GL_b(R)\), and \(s\ge1\).
All tensor products below are over R; \(*\) is transpose combined with
\(x\mapsto x^{-1}\), hence ordinary transpose after binary expansion.

Put \(n=r+a\), \(A'=\begin{pmatrix}A\\h\end{pmatrix}\), where
\(h=(1,1,0,\ldots,0)\), and \(p=(I_a\ 0)\), so \(pA'=A\).
Let \(\iota:R^{n-1}\to R^n\) insert zero at **old information coordinate 3**;
write \(\rho=\iota^*\) for restriction to the remaining coordinates.
Keep the old coordinate labels rather than renumbering them, and set

\[
A''=A'\iota,\qquad Q=\mathrm{LP}_\ell(A,B),\qquad
Q'=\mathrm{LP}_\ell(A',B),\qquad Q''=\mathrm{LP}_\ell(A'',B).
\tag{1}
\]

LITERATURE (terminology): deleting this check-matrix column is puncturing
in the convention of Han Zheng et al., Definition A.24; on kernel
codewords it is **shortening**, namely imposing zero before deleting the
coordinate. It is not unrestricted codeword puncturing.

## Lemma and proof

PROVED (conditional): zero extension identifies the shortened kernel as

\[
\iota(\ker A'')=R(g_1+g_2)\oplus\bigoplus_{i=4}^{r}Rg_i,
\qquad g_i=(e_i,V^{-1}Ue_i).
\tag{2}
\]

Indeed, the approved lemma gives the unique expression
\(u=t_\mu(g_1+g_2)+\sum_{i=3}^{r}t_i g_i\) for \(u\in\ker A'\).
Its coordinate 3 is exactly \(t_3\). Since
\(\iota(\ker A'')=\{u\in\ker A':u_3=0\}\), precisely \(t_3\)
vanishes. Thus the shortened basis is
\(g''_\mu=\rho(g_1+g_2)\), \(g''_i=\rho g_i\) for \(i\ge4\).

The old parity coordinates followed by coordinate 2 are not removed.
Their minor in A'' is still
\(\begin{pmatrix}V&Ue_2\\0&1\end{pmatrix}\), which is invertible.
Consequently A'' is split surjective, with information coordinates
\(1,4,\ldots,r\), free kernel rank \(r-2\), and no new residual sector.

For the product complexes use the previous convention
\(d_2=(I\otimes B;A\otimes I)\),
\(d_1=(A\otimes I,I\otimes B)\); double primes mean replace A by A''.
The composed chain map \(\eta:Q''\to Q\) is

\[
\eta_2=\iota\otimes I_b,\qquad
\eta_1=\operatorname{diag}(\iota\otimes I_{s+b},p\otimes I_b),\qquad
\eta_0=p\otimes I_{s+b}.
\tag{3}
\]

Both squares commute because \(A\iota=pA''\): the blocks of
\(d_1\eta_1\) and \(\eta_0d_1''\) are respectively
\(((A\iota)\otimes I_{s+b},p\otimes B)\) and
\(((pA'')\otimes I_{s+b},p\otimes B)\); the blocks of
\(\eta_1d_2''\) and \(d_2\eta_2\) are respectively
\((\iota\otimes B;(pA'')\otimes I_b)\) and
\((\iota\otimes B;(A\iota)\otimes I_b)\).
Equivalently this is the shortening map to Q' followed by the approved
augmentation map to Q.

The unchanged split B and the surviving unit minor allow the same
contractible-summand argument as before. Under binary expansion the Z
homology is identified with \(\ker A''\otimes\operatorname{coker}B\).
Let \(q_j=(e_j,0)\) represent the fixed free cokernel basis and use
\(x^m(g''_\alpha\otimes q_j,0)\) for the new Z representatives. Then

\[
\eta_Z(\bar Z''_{\mu,j,m})=\bar Z_{1,j,m}\bar Z_{2,j,m},\qquad
\eta_Z(\bar Z''_{i,j,m})=\bar Z_{i,j,m}\quad(i\ge4).
\tag{4}
\]

This is the **entire** Z image, not merely a list of admitted generators:
(2), tensored with the free cokernel basis, spans all of H1. Independence
of the old logical basis excludes every nonzero Z3-family coefficient.
All statements hold for \(1\le j\le s\) and \(0\le m<\ell\).

For the dual action, put \(v_j=(e_j,T^{-1}We_j)\) and use the old X
representatives \(x_{i,j,m}=x^m(e_i\otimes v_j,0)\).
Pullback is \(\eta_1^*\), so it restricts \(e_i\) to \(\rho e_i\).
Choose \(x''_{\mu,j,m}=x^m(\rho e_1\otimes v_j,0)\).
The pullback of \(x_{1,j,m}\) equals this representative literally,
while that of \(x_{3,j,m}\) is literally zero. Furthermore,

\[
\eta_1^*x_{1,j,m}+\eta_1^*x_{2,j,m}
=d_1''{}^*\bigl(x^m e_{\rm new}\otimes v_j\bigr),
\tag{5}
\]

since \(A''{}^*e_{\rm new}=\rho h^*\) and \(B^*v_j=0\).
Thus, as logical Pauli classes,

\[
\eta_X(\bar X_{1,j,m})=\eta_X(\bar X_{2,j,m})=\bar X''_{\mu,j,m},
\quad \eta_X(\bar X_{3,j,m})=I,\quad
\eta_X(\bar X_{i,j,m})=\bar X''_{i,j,m}\ (i\ge4).
\tag{6}
\]

Equations (4) and (6) describe the full induced logical maps. In particular,
\(k''=(r-2)s\ell\), a reduction of \(s\ell\) from Q'. At the boundary
\(r=3\), the spectator sum is empty and only the merged Z family remains
in the image. This completes the lemma.

## Scope boundary and references

PROVED: one R coordinate means all \(\ell\) cyclic positions; here it
removes the \(s\ell\) Z3 helper modes. It does not discard any logical
mode of the unchanged data code Q. The maps above are algebraic maps
between different code spaces, not physical projection or decoding steps.

OPEN: residual/rank-dropping cases, arbitrary single-position selection,
a selective PPM instrument, distances, FT preparation/readout, decoding
and runtime. No numerical exploration or physical resource estimate belongs
to this lemma. The r=3 image statement does not certify a measurement channel.

LITERATURE: [Han Zheng et al., arXiv:2607.28605v1](https://arxiv.org/html/2607.28605v1),
Definition A.24 and the zero-extension argument in Lemma A.25, fix the
terminology. [Xu et al., arXiv:2407.18490v1](https://arxiv.org/html/2407.18490v1),
Proposition 8, gives the classical map template. The approved predecessor
supplies the LP convention and split-homology argument; (2)-(6) are the
explicit conditional derivation here. No distance or FT result is imported.
