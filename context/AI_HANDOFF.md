# AI handoff

## Standing review-efficiency policy - 2026-10-01

Human-requested guidance for ALL FUTURE reviews by claude and codex, not a
special waiver for the current LP/GHZ submission. Keep the independent
cross-review requirements in AGENTS.md and coordination/PROTOCOL.md. The goal
is to remove redundant work, not to weaken scientific acceptance criteria.

1. **Review the delta and define completion first.** After mandatory startup,
   identify the changed claims/interfaces, their main failure risks, and the
   evidence needed for a verdict. Use the latest review outcome and queue;
   historical "Next: review..." paragraphs are not new assignments. Reopen
   approved, unchanged work only for a relevant dependency change or concrete
   concern. Do not turn a bounded review into the next research project.

2. **Focus independent reasoning on load-bearing claims.** Check conventions,
   core mathematical arguments, evidence labels, boundary/negative controls,
   and the distinction between logical and executable resources. Independence
   does not require a new full-size implementation of every module. Audit the
   existing verifier's logic and independence, and use a compact independent
   derivation/checker or discriminating examples where sufficient. Test
   size-specific claims at the required size; a small-case sample is not proof
   of a universal or full-instance claim. Implementer tests alone are not an
   independent review.

3. **Stage validation by risk.** Start with changed/affected tests and relevant
   boundary or mutation cases on a frozen snapshot. Run the full suite when
   shared interfaces, broad regression risk, unexplained failures, or missing
   applicable evidence justify it; do not make repeated full-suite runs the
   default for every review or documentation edit. Check known failures against
   the recorded baseline rather than silently ignoring or repeatedly
   investigating unchanged failures. Never report unrun tests as passing.

4. **Reuse evidence without confusing it with reproduction.** Record the code,
   input/configuration and relevant environment hashes (including dirty-tree
   content, not just HEAD). Reuse still-applicable prior review evidence;
   distinguish inherited, inspected and freshly reproduced checks. When new
   numerical outputs need reproduction, begin with one fresh, representative
   regeneration and a canonical-output comparison. Repeat or expand only for
   an uncovered claim, mismatch, nondeterminism, or a relevant input/code change.
   Do not overwrite the submitted canonical artifacts during review.

5. **Escalate for a stated reason, not by habit.** Before a costly full-size
   recomputation, extra independent implementation, or enlarged sweep, state
   what unresolved risk it tests and why cheaper checks are insufficient.
   Use sparse/exact representations appropriate to the problem; avoid a dense
   full reconstruction solely to make the implementation look different.
   Parallelize genuinely independent checks where useful, with nonoverlapping
   scopes, and do not have multiple workers repeat the same expensive run.

6. **Checkpoint and resume.** Save completed checks, commands/results, snapshot
   identity, elapsed time and remaining questions in the existing review record.
   Resume from that checkpoint after interruption rather than restarting.
   If the review runs beyond roughly 20-30 minutes, give an interim assessment
   and reassess the remaining plan. This is a progress checkpoint, NOT an
   approval deadline. Long-running checks should expose progress and avoid
   duplicate launches.

7. **Bound source and environment troubleshooting.** Check documented source
   paths, pinned versions and the relevant source sections first. If a private
   attachment is unavailable, state exactly which attribution/transcription
   remains unverified and request it if essential; continue separable checks.
   Do not repeatedly search the whole filesystem, re-render an entire paper,
   or rebuild environments without a concrete need. Conditional internal
   consistency does not certify fidelity to an inaccessible source.

8. **Finish when the stated evidence is sufficient.** Give a concise verdict,
   blocking findings, non-blocking limitations, and actual verification scope.
   Stop adding optional checks after the acceptance criteria are met. If a
   load-bearing issue remains unresolved, request changes or use INCONCLUSIVE
   (with a precise remaining check), never time-based automatic approval.
   Re-review fixes and their affected dependencies, not the whole unchanged
   submission. Routine bookkeeping should not trigger a new research review.

The dated cycle entries below retain their historical evidence and limitations;
their exceptionally exhaustive checks are NOT mandatory templates for future
reviews. This policy does not itself change any review verdict or scientific
result, or authorize another implementation cycle.

## Protected LP mask handoff - 2026-10-01

`T-20261001-004` is `RV-20261001-004` APPROVED (Claude review, 2026-10-01). Reviewer evidence: independently rebuilt the punctured mask M from scratch and confirmed HX_M is bit-for-bit the same row set as HX_Q restricted to S, and every HZ_M row embeds into row(HZ_Q); independently recomputed the complete 938=900+38 measured-Z dimension count and the 302-dimensional final X space using the reviewer's own previously-verified Q canonical generators (all exact matches); independently validated the no-weight<=2-logical distance algorithm against brute-force enumeration on 20 random small codes before applying a differently-coded version to the real 9600/9075-qubit codes (both certified d>=3, matching exactly); independently reproduced the masked-channel claim with a different 11-qubit explicit state-vector simulation (max residual 1.57e-16, uniform 1/128 branch probabilities); regenerated the summary byte-for-byte.

Original submission note: current submission was T-20261001-004 IN_REVIEW, RV-20261001-004 PENDING with
claude. The earlier LP/GHZ and QCLA approvals remain unchanged. Start with
docs/LP_PROTECTED_GHZ_CONTRACT.md and coordination/reviews/T-20261001-004.md;
apply the standing review-efficiency policy above.

NUMERICAL: M=LP(tilde_A with zero-based column6 deleted,A*) has9075 carriers,
rank HX/HZ5226/2911 and938 logical modes. A full-Q uniform-plus auxiliary
controls M (uniform-zero), then M is Z-read. Its complete image fixes900
unwanted canonical Zs and38 residual Zs, leaving a full-size auxiliary that
measures exactly300 canonical+2 residual Xs on data. Both Q and M have
nonzero distinct syndrome columns in both axes, certifying distances>=3.
This is not an exact distance or a circuit-FT certificate.

PROVED: complete measured algebra follows from HX restriction, supported
Z-stabilizer dimension3134-223=2911, and the302-dimensional final X space.
An independent worker also expanded all3849 mask-Z-normalizer basis vectors
once and confirmed938/900/38; repeating this expansion is not mandatory if
the efficient rank proof is independently understood. Independent logical
Kraus replay covers all128 branches and coherent spectator inputs. Mask X
frames MUST propagate onto data; dropping them is a failing negative control.

Implementer validation:103 related/new/previous-LP/Hub tests, scoped Ruff, strict mypy
--python-version3.14 and compileall pass. One fresh regeneration is byte-identical,
summary SHA256 5f7eff673a37581369d36afbc575cd6de988b5854ec51c736cb7c465077156ba.
No shared legacy modules or external pins were changed. Full repository suite
was not rerun; the relevant regression tests were. Review source transcription
only if a new discrepancy requires reopening the hash-pinned prior result.

Structural costs:18675 preparation auxiliary carriers;19200 online data+aux;
28275 if data is resident throughout preparation, all excluding QEC ancillas.
9075+9600 interface CNOTs give2 ordered matching stages, not2 code cycles.
OPEN: uniform-state FT preparation, noisy extraction/readout, decoder,
target-distance certification, strict300 mask and native performance.
Current management state: task DONE, review APPROVED, D-0037 ACCEPTED and
work lock RELEASED. No required changes. T-20261001-005 synchronizes the
remaining current-status text without changing implementation or evidence.
Next concrete action: propose a bounded FT extraction/readout or
stronger-distance study before arithmetic runtime optimization. No new
research cycle is claimed here.

Reviewer scope remains as recorded: inherited private-source transcription
was not newly verified; specific negative-control fidelities and the mask-Z
distance-inheritance proof were not separately reproduced in full detail.
The full-suite result line is an unfilled placeholder, so only the documented
103 focused tests and other stated checks are cited. Do not infer a pass count
or overwrite claude's review findings during status bookkeeping.

## LP/GHZ handoff - 2026-10-01

`T-20261001-001` is `RV-20261001-001` `APPROVED` (Claude review, 2026-10-01). Reviewer evidence: independently rebuilt the full GF(2) construction from scratch (different dense-numpy representation) and matched every rank/dimension/commutation claim exactly (A rank 223, tilde_A rank 746, Hx/Hz ranks 5226/3134, k=1240, zero commutator entries); independently reconstructed the canonical section via a different method (full augmented solve), matching the four family weights 102/108/126/114 exactly after finding and fixing an off-by-one in the reviewer's own first attempt; independently built all 1200 X and 1200 Z canonical generators and confirmed the full 1200x1200 symplectic pairing matrix is exactly the identity; derived by hand (then confirmed numerically with a fresh 16x16 dense simulation) that the X-logical action g^T is FORCED (not a free choice) given the stated Z-action g and g^2=I, including a genuine negative control; reproduced the homomorphic-coupling inclusion conditions and the d_Z=1 single-fault flip-count statistics (range 1-156, position 150 -> 1) exactly; regenerated the summary byte-for-byte. Non-blocking scope note: the seed exponents/matrices' fidelity to the private PDF attachment could not be checked (the PDF is not accessible to the reviewer), and the literal 9600-qubit physical permutation was not independently reconstructed (the logical-level 4-qubit orientation claim was verified instead, which is the scientifically load-bearing part).

Original submission note: from codex; T-20261001-001 was IN_REVIEW, RV-20261001-001 was PENDING with claude.
It implements the human's completed-LP GHZ cycle,
independent of the older QCLA submission retained below. Read
docs/LP_GHZ_HOMOMORPHIC_PREPARATION_CONTRACT.md and
experiments/runs/T-20261001-001/summary.json.

NUMERICAL: exact full-binary reconstruction gives Q_one [[9600,1240]],
1,200 paired canonical logicals and 40 residual logicals; all check,
normalizer, pairing and automorphism tests pass. PROVED: the source's graph
kernel defines Z labels, so its copy swap implements g^T on computational
bits. The correct GHZ seed is logical row 4, |000+>; the originally proposed
row 1 is preserved as a negative control (1,200 wrong-X-action failures).

The explicit 525-qubit, 525-CNOT matching helper is algebraically
code-preserving. Raw302 measures 300 canonical and two residual Xs; strict300
adds two weight-75 Z checks and measures no residual X. The auxiliary
preparation uses uniform-plus and Z projection, not the unavailable LP mask.
Both have d_Z=1. Every single helper Z is an undetected logical; a readout
fault corrupts 1..156 canonical signs. FALSIFIED is only the *unprotected
one-shot FT claim*, not the feasibility of LP homomorphic measurements.
All native time/failure/FT-concurrency fields remain null.

Implementer validation: 41 focused/replay/Hub tests, scoped Ruff, strict mypy
--python-version 3.14 (installed numpy-stub syntax) and compileall pass.
The dense verifier imports no construction code. A separate codex worker
also independently reconstructed physical matrices and quotient dimensions;
neither check replaces Claude cross-review.

Full run during development: 506 passed, two preexisting sibling-pin failures,
and one stale-import failure because the runner was updated after the verifier
module had been loaded. Fresh, code-frozen rerun of all three failing files
plus replay/Hub: 60 passed and only the two known sibling-pin failures.
No final full-suite all-green claim. Summary regenerated byte-identically;
the hash and exact commands are in the session.

Claude's subsequent review reports 46 focused/Hub passes and 528 full-suite
passes with the two known sibling-pin failures, plus byte-identical summary
regeneration. These are reviewer-reported results, not a new status-only rerun.

Current management state: task DONE, review APPROVED, D-0036 ACCEPTED and
research lock RELEASED; no required changes. Contract/session/ledger status
was synchronized by codex in T-20261001-003. Retain the review's unverified
private-PDF transcription and literal-physical-permutation scope limitations.

Next: after human authorization, construct a protected auxiliary code and
compatible homomorphic map, or evaluate a repeated-measurement/decoder schedule,
and compare to a finite surgery gadget. Do not repeat the completed review.
Do not automatically start full FT construction or a ripple-carry runtime
estimate. The earlier QCLA records remain unchanged by this follow-up.

Historical handoff follows:

Last updated: 2026-09-27
From: codex
To: claude, codex and human

## Current implementation handoff

`T-20260927-001` is `RV-20260927-001` APPROVED (Claude review, 2026-10-01). Reviewer evidence: 12 hybrid policy traces (6 branches x 2 X policies) were recomputed with Stim tableaus and match the stored PPMs and final frames exactly; axis equality between the bare and frame X policies was confirmed directly from all 64 hashed artifacts (zero axis differences, only sign differences); the every one of 66 artifacts' 441 grid cells and 504 comparison rows (29,106 and 33,264 rows total) was recomputed independently with zero discrepancies, reproducing the full headline table, the general-mode exact-zero delta at every K, the S=512 paired median 1 (not marginal 2.4), the W=256 feasible counts (24/24 vs 25/27, zero hybrid-only witnesses), the forced-witness maxima, the executed-weight statistics, and the 765/0 peak gadget ancilla counts; eight artifacts (including four not spot-checked by the implementer) regenerated byte-identically. Non-blocking: the abstract F_hybrid = G F_full identity was accepted via its reproduced consequences rather than an independent from-scratch symbolic re-derivation; final-frame signs happened to coincide between X policies on all 64 hashed witnesses.

Original submission note: `T-20260927-001` was IN_REVIEW; `RV-20260927-001` was PENDING with claude,
and its lock is REVIEW. Exact signed hybrid H-tracking/bare-CNOT traces
and independent replay cover both bare-X and frame-X, 64 hashes plus two forced
branches. Their axes and services coincide; their signs/final frames can differ.
All 1,946,736 coupling PPMs across four policies pass replay. See
`docs/H_TRACKED_BARE_CNOT_LOW_RATE_CONTRACT.md` and the generated summary.

NUMERICAL: unrestricted K=64 hybrid/full QWC median steps are 305/296;
general 263/263, exactly equal branchwise services at all six K values.
CHECK paired extra-service budget medians are QWC -6, general 0 units.
At S=512, general's paired median is 1 (range -8..11), versus a misleading
difference of marginal time medians of 2.4. W=256 fits hybrid 24/64 in both
modes versus full 25/27; forced all-one hybrid weights 572/570 fail W=512.
No general claim that bare CNOT shrinks support or speeds up the kernel follows.

Next concrete action: claude independently reviews the signed hybrid semantics,
the `F_hybrid = G F_full` physical-source-prefix identity and bilinear invariance,
capacity grid, exact branch-paired costs, four-layer automorphism obligations,
and the two-budget comparison against conjugated H. The latter condition is
`B_hybrid - B_legacy < delta`, NOT an absolute hybrid budget. Native CNOT
addressability/duration, endpoints, factories/routing and failure remain OPEN.
Do not start an ancilla construction or native mapper without the next human
authorization. Three artifacts regenerate byte-identically; all 66 old baseline
trace/lowering pairs and 1,980 common service cells match the approved data.
Full suite: 487 passed plus two known sibling-pin failures; latest related suite
107 passed, including the five tests added after full-suite collection. Strict
mypy passes 79 source files; scoped Ruff and compileall pass. Resumed canonical
summary is byte-identical. No commit made; unrelated `.claude/` is preserved.

The previous cycle's approved handoff follows as historical context:

`T-20260926-002` is `RV-20260926-002` `APPROVED` (Claude review, 2026-09-27). Reviewer evidence: the legacy conjugated-H/bare-Clifford semantics (entrance-frame H/H, F_out = F H_T D H_T) were verified with a from-scratch dense simulation over all 4,096 branches of shared-control and shared-target macros (the alternative closing-H policy fails); 24 policy traces (OOP/IP, 12 branches) were recomputed with Stim tableaus and match exactly; every stored grid entry of all 580 artifacts (statuses, service counts, exact B_crit) was recomputed with zero discrepancies, and the 18-cell selector, refined counts 218/179 of 512, medians 159/199.5, the 64-hash table and boundary witnesses were reproduced; four extra artifacts regenerated byte-identically; previous F4.1 (PDF pins) is resolved. Non-blocking: cross-reference the reviewed full-conjugation logical envelope so B_crit is not read as a knife-edge; keep the QWC/general cohort caveat when quoting. Submission note: both pinned
PDFs resolve the previous F4.1 item below. The paired comparison and selected
512-hash refinement are complete: 580 branch/variant instances, 8,067,156
independently replayed coupling PPMs. IP/weight-256 fits are legacy PPM 512/512,
tracked QWC 218/512 and fixed general lowering 179/512. Other cells retain 64
hashes. Native time/space/failure and legacy Clifford service/feasibility remain
OPEN/null. The detailed contract is `docs/LOW_RATE_CLIFFORD_BREAK_EVEN_CONTRACT.md`.

Review is complete with no required changes. Management state: task DONE,
review APPROVED, decision D-0034 ACCEPTED, documentation lock RELEASED.
No further review of this implementation is pending. The status-only follow-up
passed 43 focused/Hub tests and `git diff --check`; no commit was made.

Next concrete action: propose a bounded follow-up that specifies one realizable
legacy Clifford service and tests its branch-dependent B against Bcrit on the
same branches; start only after human authorization. Do not compare median B
with median Bcrit without branch pairing; different tracked modes may also
have different common-feasible subsets. Keep the review's non-blocking notes
visible: logical Clifford envelopes are not native costs, and unselected cells
have only 64 hashes. See `coordination/reviews/T-20260926-002.md`.

Validation: full 454 pass + two unchanged sibling-pin failures; latest focused
and Hub 43 pass after the saved-output audit was added; Ruff/compileall and strict
mypy (78 files) pass. Seven fresh artifacts (both variants -2/-1/0 and IP 511)
are byte-identical; checkpoint-resumed summary/SVG also match exactly. The
independent rational audit checks all artifact hashes, 15,192 paired rows and
234 aggregate records. All 108 plot labels match data and the rendering was
visually checked. No commit made; unrelated `.claude/` remains untouched.

The preceding cycle's approved handoff follows for context:

`T-20260926-001` is `RV-20260926-001` `APPROVED` (Claude review, 2026-09-26). Reviewer evidence: the signed trace was recomputed with Stim Clifford tableaus for 10 width-256 traces (OOP/IP, branches -2, -1, 0, 17, 63) with every PPM and the final frame equal; a from-scratch dense simulation verified shared-control and shared-target tracked-H macros over all 4,096 branches (negative control fails); the measurement gadget was verified for all 162 signed Paulis on 1-3 qubits including odd Y; all 132 stored artifacts passed an independent regularity/signed-product/packing audit and every grid cell and headline median was reproduced; the cited Cowtan et al. section 3.6/Definition 3.14 and Zhang-Li appendix I were read and match. Non-blocking: pin the two PDFs; executed maximum weight (not step count) changes by about 10% under another valid regularization order.

Original submission note: the human
redirected the next mapping workload to parameterized parallel low-rate surgery.
The new modules do not depend on the separately approved partial-clearing task below.
Full H/CNOT frame tracking preserves signed X/Y/Z observables; general commuting
sets are explicitly regularized and lowered to verified measurement gadgets.
K, per-executed-PPM weight, and sum-support constraints are applied after lowering.

The first checkpoint includes 64 hashed plus two forced branches for each
width-256 OOP/IP workload, 730,026 independently replayed coupling PPMs, full
compressed traces/lowerings, capacity grids, and representative CCZ/service
timelines. Under unlimited support, median QWC/general surgery steps are
OOP 92/111 and IP 296/263 at K=64, versus OOP 54/44 and IP 249/104 at unlimited K.
In the explicit CHECK service example, IP K=64 takes 330.5/359.5 units, while
K=256 takes 288.5/216 units: fewer primary steps need not mean shorter time.
Weight 512 admits all hashed witnesses but neither all-one witness. Real Clifford
closure proves even Y parity, so this workload does not need logical Y catalysts.

Post-review synchronization (codex, 2026-09-26): the task is DONE, review is
APPROVED, decision D-0033 is ACCEPTED and the work lock is RELEASED. The contract
now records the review's regularization-order sensitivity beside the weight-cap
counts (F4.2); unchanged step counts in the tested cases are not a general theorem.
Next: pin the two versioned PDFs with SHA-256 (F4.1, still OPEN), then pursue
the proposed boundary refinement to 512 hashed witnesses (NOT yet run) and
code-specific service/support calibration. Do not interpret the hypothetical
1ms/unit conversion as neutral-atom runtime.

Validation: latest focused suite 26 passes; the earlier-collected full run has
411 passes and the two known sibling-pin failures. All six forced/hash-0 artifacts
regenerate byte-identically. See the task session for exact scope and environment.
Reviewer validation additionally records 416 full-suite passes and the same two
known sibling-pin failures, plus four further byte-identical regenerations.
No git commit was made; preexisting dirty work and the approved review are preserved.

## Reviewed partial-clearing handoff (`RV-20260909-001` `APPROVED`)

`T-20260909-001` implements and profiles conservative target-component partial
Clifford-frame clearing for the reviewed in-place QCLA workload.  It exposes
the byproduct convention `physical = F ideal` and enforces
`G = F_out U F_in^dagger`.  For each simultaneous H layer, the incoming frame
is stably partitioned as `F_in = A R`: every interaction component touching an
H target is materialized as `U_H A^dagger`, while disjoint components remain
as `F_out = R`.  Width 5 checks factorization, physical action, and commutation
on every logical X/Z generator, giving 11,520 projective checks with zero
mismatch.

For the width-256 coherent IP 30-macro/60-candidate workload and 32 fixed
branch witnesses, partial clearing has median 3,843 literal CNOT generators,
284 CNOT batches, 380 serialized logical layers, presented PPM weight 11
(sampled maximum 16), and final-frame size 1,862.  Full clearing gives
4,250/176/270, PPM weight 2/2, and final-frame size 1,273.  Thus partial
clearing saves 9.58% in literal CNOT count but loses in the present same-wire
depth envelope and leaves more support.  It remains a compiler Pareto point,
not a selected native implementation.

`RV-20260909-001` is `APPROVED` (Claude review, 2026-09-26); see
`coordination/reviews/T-20260909-001.md`.  The reviewer confirmed the frame
convention against the approved compiler, cross-checked frame accumulation on
192 width-5 rows (192/192 agree), and reproduced every width-256 headline with a
second implementation.  Non-blocking requests: state that the CNOT-batch
envelope depends on ASAP direction (forward-time scheduling of the chronological
circuit gives 148/249 instead of 176/284; layers 270/379 are essentially
invariant), note that literal counts depend on intra-layer generator order,
and add the compiler cross-check as a regression test.  Next, after review, the
scientific task is a global Clifford resynthesis/native-mapper frontier for
full versus partial clearing.  Do not convert any current layer number into
runtime: addressable H/CNOT, surgery geometry/capacity, decoder/reaction,
factory/buffer, memory, cycles, physical qubits, and failure remain open.

See `docs/PARTIAL_CLIFFORD_FRAME_CLEARING_CONTRACT.md` and
`experiments/runs/T-20260909-001/summary.json`.

## Public visualization

`T-20260907-003` published the reviewed OOP/IP width-256 standalone visualization at
`https://qcla-oop-ip-width256.sleek-clove-8896.chatgpt.site` with public access.
The deployed page is byte-identical to the reviewed local standalone preview and
an external request returned HTTP 200. This task changes presentation/access only;
all review conclusions and the next scientific action below are unchanged.

## Current review handoff

`T-20260907-002` is `RV-20260907-005` `APPROVED` (Claude review, 2026-09-07).
It evaluates both reviewed width-256 compressed workloads
under one deterministic 512-branch protocol. For each candidate level and
global branch, it records the maximum presented logical PPM support weight;
the compact table retains p50/p95/p99, the maximum over 510 hashed
assignments, all-zero/all-one boundary values, the full sampled maximum, and
the reviewed support ceiling.

OOP/IP largest p95 values are 168/188, p99 values are 198/222, and
hashed-assignment maxima are 223/248. Both full sampled maxima are 509 because
the forced all-one branch dominates. The separate OOP exact/IP may-support
ceilings remain 1,003/1,006, with largest same-level gaps 494/622. Every
fresh-resource X phase has exact weight one. The 512 assignments are
deterministic numerical witnesses, not random population estimates or
exhaustive maxima.

The primary implementation uses sample-packed bit planes. A separate scalar
verifier imports none of the sampler and reconstructs all 46,080 level--branch
values and 11,326,464 branch--PPM evaluations one branch at a time, including
assignment/vector hashes, nearest-rank quantiles, ceilings, and exact X
phases. Mutation tests reject vector, quantile, and native-output changes.
Native cycles, runtime, physical qubits, failure, connected support, routing,
decoder/reaction, and factory/buffer service remain null/open. See
`docs/WIDTH256_OOP_IP_BRANCH_WEIGHT_SAMPLING_CONTRACT.md` and
`coordination/reviews/T-20260907-002.md`.

The reviewer independently reimplemented the support-propagation rule a
**third** time, using a deliberately different data structure (plain
`dict[str, set[str]]` columns with set symmetric difference) rather than
either the scheduler's 512-wide bit-plane packing or the shipped replay's
per-branch integer bitsets. Using this independent implementation to compute
only the two *deterministic* forced boundary branches (all outcomes zero,
all outcomes one) for both OOP and IP, the reviewer found and fixed a bug in
their own first attempt (an incorrect XOR-toggle condition), then matched
the corrected result to the claimed full sampled maximum of 509 at the exact
claimed level for both variants (OOP level 29, IP level 31). The reviewer
separately wrote a script that recomputes every nearest-rank quantile,
hashed-assignment maximum, and sampled-to-ceiling gap directly from the
stored 512-entry vectors for all 90 candidate levels (not re-deriving the
physics, just the statistics layer) and matched the contract's complete
headline hotspot table exactly, including every recorded tie. The reviewer
also confirmed the OOP/IP evidence-label boundary is enforced structurally
in the dataclass `__post_init__` guards, not merely asserted in prose, and
spot-checked the out-of-repository rendered OOP/IP switch view (a local
file, not a hosted claim), finding its byte size and every headline number
consistent with the reviewed data. Two independent byte-identical
regenerations matched the implementer's five recorded SHA-256 prefixes
(`4AEB8EDA`, `60D7DD5E`, `66D96F73`, `B0720F02`, `2E36BB9F`) exactly.

This closes the width-256 OOP/IP structural comparison cycle. No task ID is
currently claimed for the next step (a native mapper/frame-materialization
policy for the certified logical candidates, or closing the IP support
envelope's remaining 29 `CHECK` levels).

## Previous approved handoff

`T-20260907-001` is `RV-20260907-004` `APPROVED` (Claude review, 2026-09-07). It applies the approved positive-control CCX commutation rule to the reviewed width-256 in-place modulo-`2^256` QCLA while treating intervening X and CNOT source layers as global ordering barriers. A complete 3,019,653-pair scan and an implementation-independent replay agree with the streaming recurrence: 2,012,691 pairs retain dependencies, 1,006,962 are admitted, the critical path has thirty events, and the exact model-relative schedule is 30 macros/60 two-phase candidates versus the source-aligned 34/68 baseline.

Exact logical demand is 2,458 fresh CCZ states, 14,748 PPMs, 4,916 target-H applications, and peak 255 CCZ states/target-Hs per macro. The source uses 495 ancillas and 1,007 fully resident values; source-coordinate liveness peaks at all 495 ancillas. Support is deliberately mixed-evidence: 31 levels are exact and 29 retain sampled/may-support bounds, with maximum sampled single-branch PPM weight 509, sound weight upper bound 1,006, possible union 1,770, possible contact 634, and 118,038 unwitnessed may-incidences. Possible unions are not simultaneous branch weights, connected code support, or native geometry.

The independent replay reconstructs every pair decision, rank, parent, barrier kind, demand row, and support envelope without importing the new scheduler, and exhaustively verifies the reordered arithmetic for widths 2--8 over 87,376 input pairs. It rejects rank, support, and finite-native-output mutations. Five focused tests, Ruff, strict mypy on 67 source files, compileall, and the full suite (380 passes plus only the two known sibling-pin failures) are complete. Native cycles, seconds, physical qubits, failure, addressability, routing, decoder/reaction service, and factory/buffer service remain null/open. See `docs/WIDTH256_IP_COMMUTATION_AWARE_QCLA_CONTRACT.md` and `coordination/reviews/T-20260907-001.md`.

The reviewer independently reimplemented the complete O(n^2) pairwise
dependency and longest-path computation from scratch (not importing the
reviewed scheduler or its shipped replay module) directly against the real
width-256 in-place source trace, and matched every headline number exactly:
2,458 CCXs, 1,019 CNOTs, 510 X gates, 3,019,653 pairs, 2,012,691
dependencies, 1,006,962 admissions, 12,996 noncommuting pairs, macro-depth
30, the complete 30-element macro-layer size vector, and the widths-2--8
bridge table `(2,2),(4,4),(6,6),(12,8),(12,8),(14,10),(14,10)`. It
independently verified by direct hand calculation that `X` on a CCX control
does not commute with that CCX (`X` then `CCX` gives a different result than
`CCX` then `X` for `c0=0,c1=1,t=0`), confirming that treating only CNOT
layers as barriers -- omitting X -- would have been an unsound generalization
of the OOP rule. It confirmed the sampled/may-support/exact evidence labels
are enforced structurally (not just asserted) and numerically exact: 31 of
60 support levels are exact and 29 retain `CHECK` gaps, the sum of
unwitnessed may-incidences is exactly 118,038, and every sampled-weight/
may-support/contact bound in the generated data matches the contract table.
Two independent byte-identical regenerations matched the implementer's five
recorded SHA-256 prefixes (`9EE1D02E`, `4EDB7E65`, `5CCC22D7`, `FF2CC9C6`,
`353B7AE4`) exactly.

This closes the entire joint-CCX/commutation-aware validation cycle
(`T-20260906-001` through `T-20260907-001`) for both the OOP and IP width-256
workloads. No task ID is currently claimed for the next step.

`T-20260906-004` is `RV-20260907-003` `APPROVED` (Claude review, 2026-09-07).
The selected width-256 result is the exact model-relative commutation-aware
unitary schedule, not the raw measurement-cleanup relaxation.

The clean OOP source has 1,229 CCXs, 766 CNOTs, 240 prefix scratch values,
seventeen source CCX layers, and 34 source-aligned two-phase candidates. The
new compact recurrence stores one dependency/rank record per CCX and agrees
with a complete 754,606-pair oracle: 251,125 pairs retain dependencies,
503,481 are admitted, and 3,249 are noncommuting. The resulting fifteen
macro-layers have a matching fifteen-event critical path, proving 30
two-phase candidate levels inside the explicit unlimited-capacity logical
model.

Support is recomputed at each common macro-entry rather than feeding one
same-macro event's corrections into the next. All 7,374 PPM profiles replay.
The peak macro has 255 CCZ states, 765 PPMs per phase, and 255 distinct target
Hs. Across levels, maximum possible PPM weight is 1,003, possible union is
1,647 including fresh resources, and possible contact is 54. These are exact
logical hypergraph envelopes, not simultaneous branch weights, connected
code support, or native geometry. Active source values peak at 1,004 versus
1,008 under fully resident allocation. Bare CNOT source layers contain
254/256/256 gates.

The width-5 cleanup channel remains valid, but its naive width-256 promotion
fails a new axis gate. Each of 240 prefix candidates has a branch where the
last-use event's conditional control--control `CZ(p,q)` presents cleanup
`X(p)` as mixed-axis `X(p)Z(q)`. Early source cleanups are also followed by up
to 236 other CCXs, so their conditional frame cannot be discarded. No
cleanup CCX is removed, no raw-removal depth is reported, and the cleanup
alternative falls back to unitary 15/30. This is `FALSIFIED` only for the
current Z-only/X-only high-rate family, not for the abstract
measurement-uncompute identity.

Focused tests (5), Ruff, strict mypy on 64 source files, and the independent
replay pass. The replay reconstructs all pairs, nodes, levels, PPM profiles,
lifetimes, and mixed-axis witnesses and rejects rank, axis-admission, and
finite-output mutations. The full suite has 375 passes and only the same two
unrelated sibling source-pin failures. Native cycles, seconds, physical
qubits, failure, addressability, routing, reaction/decoder latency, and
factory/buffer service remain null or open. See
`docs/WIDTH256_COMMUTATION_AWARE_QCLA_CONTRACT.md` and
`coordination/reviews/T-20260906-004.md`.

The reviewer independently reimplemented the complete O(n^2) pairwise
dependency and longest-path computation from scratch (not importing the
reviewed scheduler or its shipped replay module) directly against the real
width-256 source trace, and matched every headline pair-oracle number
exactly: 1,229 nodes, 754,606 pairs, 251,125 dependencies, 503,481
admissions, 3,249 noncommuting pairs, macro-depth 15, and the complete
15-element macro-layer size vector `[255, 253, 126, 64, 34, 23, 20, 28, 40,
61, 66, 72, 53, 70, 64]`. It independently verified the streaming
recurrence's soundness (redundant/non-minimal dependency edges never shorten
or lengthen the true longest path, so tracking only the highest-rank
predecessor per conflicting qubit name per barrier segment is exact, not an
empirical shortcut). It algebraically re-derived the cleanup mixed-axis
identity `CZ(p,q) X(p) CZ(p,q) = X(p) Z(q)` from explicit basis-state action,
and independently confirmed -- for all 240 candidates, not a sample -- that
each has a well-defined last-use CCX with the target as one of exactly two
controls and a read-only intervening history, that the earliest candidate
precedes exactly 236 later CCXs, and that every candidate's
`released_target_later_ppm_use_count` is zero. It confirmed this task's
`FALSIFIED` cleanup-axis finding is additive to, not in conflict with, the
narrower classical-channel/relative-phase claims already approved in
`RV-20260907-001` and `RV-20260907-002` (neither of which claimed native
PPM-family compatibility for the cleanup measurement). Two independent
byte-identical regenerations matched the implementer's five recorded SHA-256
prefixes (`060adb65`, `26c984c1`, `5d506b6b`, `9dc4cc64`, `ef478fc5`) exactly.

The next unassigned item is a coherent native mapper/finite backend for the
certified logical candidate levels and support hypergraphs (see "Next
concrete action" below); no width-257+ or further commutation-aware task is
currently claimed.

Post-review bookkeeping is synchronized: `D-0029` is `ACCEPTED`,
`R-20260907-008` through `R-20260907-010` record the approved validation,
the task/session status is complete, and the work lock is released. This
normalization changes no scientific result or implementation.

## Previous approved handoff

`T-20260906-003` is `RV-20260907-002` `APPROVED` (Claude review, 2026-09-07).
It implements the separate commutation-aware clean OOP-QCLA dependency model
at widths 2--8 after the approved width-5 semantic gate.

Every ordered CCX pair is independently truth-table classified. The DAG keeps
source order for noncommuting target--control overlap and for any pair crossing
a source CNOT layer; other pairs may share one approved common-frame macro.
Earliest longest-path ranks form legal layers and meet an explicit critical-
path lower bound, proving exact macro-depth within this complete logical model.
Source/unitary/measured depth is `1/1/1, 2/2/2, 3/3/3, 6/4/3, 6/4/4,
7/5/4, 7/5/5`. With two direct-CCZ candidate levels per macro, width 5 is
therefore source 12, unitary 8, and measured cleanup 6.

The measured variant removes `0/0/0/1/1/2/2` certified final cleanup CCXs.
Independent complete arithmetic and phase replay shows that cleanup reduces
depth at widths 5 and 7 but not at 6 or 8, where another critical path remains.
The verifier imports neither the new scheduler nor the joint direct-CCZ
compiler and checks 776 pair decisions, 39,824 pair truth-table rows, 174,752
arithmetic runs, 337,920 measured branch columns, and 337,908 relative-phase
pairs with zero mismatch.

The result deliberately retains all six outcome tokens per predecessor CCX at
each inter-macro reaction boundary. This frontier is conservative `CHECK`;
the minimal outcome subset and reaction duration remain unresolved. The exact
claim is therefore logical macro-depth only, not native cycles or time. Width
256 has not been rerun and remains at its reviewed source-aligned 34 candidate
levels. Placement, routing, ports, memory, decoding/reaction, factory/buffer,
physical qubits, failure, and every finite output remain null.

Eighteen focused and 55 related tests pass. The full suite has 370 passes and
only the same two unrelated sibling source-pin failures. Ruff and strict mypy
pass; compileall, Hub validation, and final deterministic regeneration are
recorded in `coordination/sessions/T-20260906-003.md`.

The reviewer independently reimplemented the entire pairwise-dependency and
ASAP-longest-path scheduler from scratch (not importing the reviewed
scheduler or its shipped replay module), running it against the real,
already-reviewed `build_oop_qcla_trace` for every width 2--8 and both
variants, and reproduced the exact `1/1/1, 2/2/2, 3/3/3, 6/4/3, 6/4/4, 7/5/4,
7/5/5` macro-depth table exactly. It independently re-derived all five
aggregate replay totals from first principles (776 pairs via
`sum(C(n,2))`; 39,824 truth-table rows via `sum(2^|union support|)`; 174,752
arithmetic inputs via `sum(4^width)*2`; 337,920 branch columns and 337,908
relative pairs via the branch/relative-pair formulas applied to widths 5--8)
and matched every one exactly. It verified the ASAP-layering optimality claim
mathematically: a dependency edge always strictly increases longest-path
depth, and this propagates correctly through transitive chains even without
an explicit transitive edge, so the "PROVED optimal within this stated
logical model" claim is not merely an empirical observation. It hand-traced
both width-8 measurement-uncompute cleanups from the raw gate list (producer,
last quantum use, frame propagation) and found the generated
`cleanup_records` matched exactly, including two disjoint final frame
supports. It also located and spot-checked the out-of-repository public
width-5 "Parallelization audit" page (a local file on this machine, not a
remote claim) and found its `CHECK`/"not physical time" labeling and its
"Width 256 is not revised yet" disclaimer consistent with the reviewed
claims, though it could not independently verify the page's full rendering.
See `docs/COMMUTATION_AWARE_QCLA_SCHEDULING_CONTRACT.md`, experiment
`E-20260906-003`, and `coordination/reviews/T-20260906-003.md`.

Approval of `RV-20260907-002` clears the dependency gate for the still-unassigned
`T-20260906-004` width-256 structural rerun.

## Previous approved handoff

`T-20260906-002` is `RV-20260907-001` `APPROVED` (Claude review, 2026-09-07).
It closes the bounded logical-semantic gate required before building a
separate commutation-aware dependency trace; it does not yet admit that
trace, an exact schedule, or a width-256 rerun.

The exact positive-control CCX truth-table classifier proves that two CCXs
commute iff neither target is a control of the other. It checks all 45 pairs
among the ten pinned width-5 source CCXs (36 commuting, nine noncommuting;
2,040 basis rows) plus synthetic representatives of every overlap class. The
four proposed unitary macro-groups have sizes 4/3/2/1 and pass common-frame
primitive factorization with ten fresh resource triples, all 64 single-event
branches, both actual shared-control anchors, one synthetic shared-target
anchor, canonical corrections, and no event-to-event reaction edge. The
largest joint probability/operator residual is
`5.692061405548898e-19`/`2.4854698590557027e-18`.

The measured-cleanup alternative replaces final operation
`qcla-oop:000012` by destructive `X(p:1:1)` plus outcome-conditioned
`CZ(b:2,b:3)`. Independent full-width replay passes all 1,024 input columns,
2,048 outcome branches, and 2,046 relative-phase comparisons with zero output
or dirty-ancilla mismatch. The outcome-dependent frame is not discarded: it
propagates through four later CNOTs and conservatively reaches
`{a:2,a:3,b:2,b:3,z:2,z:3}`; the width-5 suffix contains no later PPM.

The semantic result admits the four unitary and three measured-cleanup
macro-groups as inputs to `T-20260906-003`. Their 8/6 two-phase values remain
`CHECK` envelopes, not schedules, lower bounds, optimality results, surgery
rounds, or time. The reviewed width-5 12-level and width-256 34-level baselines
remain unchanged, and native cycles, seconds, physical qubits, and failure
remain null. Assumption identifiers were normalized at task entry: H
teleportation retains `A-0045`, joint direct CCZ is `A-0046`, and measurement
uncompute is `A-0047`. Fourteen focused and 64 related tests pass; the full
suite has 352 passes plus the same two unrelated sibling-pin failures. See
`docs/JOINT_DIRECT_CCZ_WIDTH5_CONTRACT.md`, experiment `E-20260906-002`, and
`coordination/reviews/T-20260906-002.md`.

The reviewer independently re-derived every headline number from scratch
without importing the new compiler or its shipped replay module: a
from-scratch commutation classifier reproduced the exact 36/9 pair split and
overlap-kind breakdown; a differently-structured tensor-based statevector
simulator (explicit `numpy` reshaping/`tensordot`, not the reviewed code's
bit-shift indexing) reproduced the joint-injection channel for both real
shared-control anchors and matched the probability/operator error magnitudes
to the same digit; the measurement-uncompute phase-cancellation identity was
re-derived algebraically (`p:1:1` already equals `b:2 AND b:3` at the
replaced gate, so the destructive-`X` and conditional-`CZ` phases are
identical and cancel to a constant `1/sqrt(2)`); and the four-gate
frame-propagation and final support `{a:2,a:3,b:2,b:3,z:2,z:3}` were
confirmed by hand-tracing the raw gate list. Regenerated artifacts twice from
a clean directory, byte-identical both times and matching the independent
derivations. Reran the full suite (352 passed, same two known unrelated
failures). The reviewer also flagged that the assumption-ID collision this
task fixes (`A-0045` reused by both the H-teleportation and joint-CCX
assumptions) was present when `RV-20260906-001` was approved and was missed
in that review; it is recorded as a bookkeeping oversight, not a scientific
defect, and this task's fix and transparent disclosure in
`docs/JOINT_CCX_QCLA_REEVALUATION_CYCLE.md` are correct.

`T-20260905-001` is `RV-20260905-001` `APPROVED` (Claude re-review,
2026-09-06), closing the sole defect from the first-pass review. The
`one_bit_h_teleportation` option is now a self-derived `NUMERICAL` identity;
it no longer cites Xu et al. The Xu Figure 11(c) `LITERATURE` citation remains
only on measurement CNOT. A new independent operator-channel verifier checks
all four `ZX`/destructive-`X` outcome branches for the `|0>` carrier, obtains
probability `1/4` per branch within `5.551115123125783e-17`, and matches H up
to the branch Pauli correction with maximum Frobenius residual
`1.1102230246251565e-16`; the reviewer independently re-derived this exact
channel with a second, differently-coded script and matched every number
including the scalar corrections (`0.5, 0.5, 0.5, -0.5`). Replay rejects
renewed Xu attribution or an H evidence label other than `NUMERICAL`, and the
reviewer confirmed the corresponding mutation test actually exercises this
guard. `A-0042` now records only the cited measurement-CNOT assumption and
`A-0045` records the H identity. Six focused tests, 11 combined strategy/Hub
tests, Ruff, strict mypy, compileall, generation, replay, and mutation checks
pass; the full suite has 338 passes and only the same two unrelated
sibling-pin failures -- all independently reproduced by the reviewer, including
two independent byte-identical artifact regenerations matching the
implementer's recorded hashes exactly. The layer counts, logical envelopes,
frame-conjugated-H plus bare-CNOT policy, and null native outputs are
unchanged from the first pass.

Review history: `T-20260905-001` received `RV-20260905-001`
`CHANGES_REQUESTED` (Claude review,
2026-09-06). The task separates the logical H/CNOT frame policy from the
code-side realization question, and the review confirmed every part of that
separation except one citation.

Under `physical = C^dagger logical`, the independently replayed six-row matrix
finds that only frame-conjugated H generally preserves the existing Z-only
direct-CCZ phase-1 invariant. Bare or tracked H has an explicit two-qubit
mixed-axis/Y witness. All three CNOT modes preserve Z type by closure of the
`X/Z/CNOT/CZ` subgroup, but bare/tracked CNOT can grow, reroute, and retain
branch dependence in later support. Fresh-resource phase-2 readouts remain
X-only in every case. The proposed logical default is therefore
frame-conjugated H plus bare CNOT, pending review.

Width-256 OOP/IP has 17/34 Toffoli-bearing layers and 3/4 CNOT-only layers,
giving 34/68 H layers with maximum parallel demand 255 and CNOT-layer maximum
256. Starting from the reviewed 34/68 candidate levels, one-layer-H plus SIMD
CNOT gives conditional overlap totals 54/106 or strict totals 71/140.
One-bit-H teleportation plus measurement CNOT gives 94/182 or 111/216. These
are logical primitive-layer envelopes only. The overlap version assumes the
closing H/H-teleport step can overlap the disjoint fresh-resource-X phase.

The H teleportation gadget needs one provisioned `|0>` carrier per parallel H
and ordered `ZX`, `X` measurements; the CNOT gadget needs one `|+>` scratch
per parallel CNOT and ordered `ZZ`, `XX`, `Z` measurements. Neither consumes
T/CCZ magic states. H-SWAP and H teleportation implement bare H, not the
selected frame-conjugated H, unless the frame is cleared, the target is
proved H-safe, or the whole conjugated-H/direct-CCZ event is co-designed.

RASCqL Table 1/2 values are retained only as an incompatible-domain `CHECK`
comparator. They yield OOP 65.1/73.6 ms and IP 124.2/141.2 ms for the
overlap/strict H-SWAP+tCNOT arithmetic while excluding relabel debt. They are
not current direct-CCZ runtime. Current-backend cycles, seconds, physical
qubits, and failure remain null.

Five focused tests pass; the full suite has 337 passes and only the two known
unrelated sibling-pin failures. Ruff, strict mypy, compileall, deterministic
generation, independent replay, and mutation checks pass. See
`docs/HIGH_RATE_QCLA_H_CNOT_STRATEGY_CONTRACT.md`,
`experiments/runs/T-20260905-001/summary.json`, and
`coordination/reviews/T-20260905-001.md`.

The review independently reconstructed the H/Y witness and the CNOT-closure
argument from explicit numpy matrices, independently re-extracted every
width-256 OOP/IP layer count directly from the reviewed QCLA builders (not the
new module) and matched them exactly, independently recomputed every
strict/overlap added-layer total and the RASCqL-domain millisecond totals from
the stated formulas, and directly pixel-verified the RASCqL Table 1/2 values
and the CNOT-teleportation gadget against Xu et al. Figure 11(c) with zero
discrepancies. It reproduced the 5 focused tests, ran ruff/strict
mypy/compileall clean on all new files, and regenerated the six-artifact
experiment twice with independently confirmed byte-identical hashes.

The review found one defect: the `one_bit_h_teleportation` execution option's
citation to "Xu et al. 2024, arXiv:2407.18490v1, Figure 11" is wrong. Page 28
of that source shows only (a) generic `ZZ`+destructive-`X` teleportation on a
`|+>` ancilla, (b) a teleported S gate, and (c) measurement-based CNOT (the
gadget correctly cited elsewhere in the same record); it contains no
one-bit-H-teleportation panel, and the paper's actual Hadamard method
(Section 5) is an unrelated global fold-transversal H-SWAP technique. An
independent from-scratch numpy simulation (20 random states, exact
statevector arithmetic) confirms the `ZX`-then-`X`, `|0>`-ancilla gadget
described in the contract is nonetheless mathematically correct -- it reaches
fidelity 1.0 to `H|psi>` on every outcome branch via one deterministic Pauli
correction -- so this is a citation/evidence-label defect (the claim should be
`NUMERICAL`/re-sourced rather than `LITERATURE`/Xu-Figure-11), not a
computational error, and it does not affect any other finding, the width-256
layer-demand numbers, or the null current-backend outputs. See
`coordination/reviews/T-20260905-001.md` for the complete finding list and
required changes.

That requested change has now been implemented in
`src/ecdlp_ftqc/analysis/qcla_clifford_strategy.py`, the contract, and the
assumption ledger: the accurate CNOT half retains its
`LITERATURE`/Xu-Figure-11(c) label, while the H half is recorded separately as
the self-derived `NUMERICAL` assumption `A-0045`. The re-review independently
verified the fix rather than trusting the implementer's report: it re-read the
updated `ExecutionOption` record and the new
`verify_one_bit_h_teleportation_channel`/`_h_teleportation_branch_operator`
functions, ran them directly, then wrote a second independently-coded script
using a different derivation (explicit basis-vector projectors and a
separately-derived probability formula) that reproduced the identical branch
operators, scalars, and error magnitudes to the last bit; confirmed the
mutation-rejection test genuinely reinstates an Xu citation and checks replay
raises on it; reran the focused and full test suites, ruff, and strict mypy;
and regenerated the experiment twice, matching both the implementer's recorded
hashes and each other byte-for-byte. `T-20260905-001` is now `DONE` and its
lock is `RELEASED`. See `coordination/reviews/T-20260905-001.md` for the
complete re-review.

`T-20260903-002` is `RV-20260903-002` `APPROVED` (Claude review, 2026-09-03).
It adds logical-support hypergraphs for the reviewed source-aligned direct-CCZ
candidate levels and separates exact possible-support unions, sampled lower
witnesses, and sound may-support upper envelopes.

The initial hypothesis is `FALSIFIED`: Z-type closure does not make support
outcome-independent. The first exact OOP width-5 witness is
`direct-ccz:000005:ppm:zz_0`, where logical value `a:0` has activity ANF
`direct-ccz:000000:outcome:zz_1`. Its zero/one assignments remove/add that
component. Exact OOP/IP widths 5 and 8 match every component ANF and the first
witness in the reviewed full symbolic trace.

All 19 selected OOP widths through 257 use exact Boolean-ANF possible-support
propagation. At OOP width 256, 7,374 PPMs contain 1,924 branch-dependent
profiles; the largest exact possible-support union is 1,003 and the largest
within-batch possible-contact count is 129. A possible-support union may
combine values occurring in different branches and is not a simultaneous
branch weight.

IP widths above 8 use a sound may-support upper envelope plus 512 deterministic
concrete branches. At width 256, 14,748 PPMs contain 5,355 observed branch-
dependent profiles. The witnessed possible-support-union lower bound is 935,
the maximum support weight actually present in one sampled branch is 509, and
the witnessed contact lower bound is 523. The may-support upper bounds are
1,006 and 567. Because 4,462 profiles retain 118,501 unwitnessed may-
incidences, large-IP exact support remains `CHECK`, not `PROVED`.

The independent replay imports neither compiler nor scheduler, checks source
identity/counts for all 38 certificates, and reconstructs the full logical
support claims at widths 5, 8, and 256, including both 256-bit hypergraphs.
Noncanonical correction maps and hypergraph mutation fail closed. All native
schedule, surgery-round, runtime, placement/routing, processor/factory,
physical-qubit, and failure outputs remain null. See
`docs/DIRECT_CCZ_QCLA_SCALABLE_SUPPORT_CONTRACT.md`,
`experiments/runs/T-20260903-002/summary.json`, and
`coordination/reviews/T-20260903-002.md`.

Rather than hand-derive the two-sided CNOT-conjugation tableau algebra (an
error-prone manual exercise that produced suspicious intermediate results on
paper), the reviewer independently cross-checked the certificate's exact
support activities against the already matrix-verified full symbolic
compiler's `presented_observable` z/x-components using hand-written
comparison code -- not the reviewed comparison function -- across all 522
PPMs at widths 5 and 8 for both variants, finding zero mismatches and
correctly identifying every branch-dependent component. The reviewer
independently reproduced the outcome-independence falsification witness by
direct inspection, matching the claim exactly; confirmed the large-IP
may-support envelope is sound by construction (every update is a monotonic
set union, never a removal) by reading the code rather than only observing
it empirically; and verified all width-256 bound orderings (witnessed-union
<= may-support upper bound, single-sampled-branch weight <= witnessed union,
witnessed contact <= upper contact) hold from the generated summary.
`git diff --stat` confirmed the task touches no previously reviewed
compiler, architecture, batching, or compatibility-certificate code.

No task currently holds an active lock; `T-20260903-002`'s lock is
`RELEASED`. The next open item is implementing one coherent native mapper or
explicit frame-materialization policy for the branch-dependent width-256
support hypergraphs (no task ID claimed yet), alongside the separate
factory/buffer/routing and AutoCCZ finite-field work already tracked below.

`T-20260903-001` is `RV-20260903-001` `APPROVED` (Claude review, 2026-09-03).
It replaces the large-width `CHECK` two-phase envelope with a linear-size
logical compatibility certificate. Under the reviewed frame normal form,
conditional `X/Z/CNOT/CZ` generators preserve branchwise Z-type Paulis. Each
source layer's phase-1 resource-data `ZZ` PPMs are therefore same-axis,
commuting, and Y-free; phase-2 resource `X` readouts are disjoint on globally
fresh resource values absent from the frame. The certifier also checks exact
source/event DAG preservation, support-disjoint source layers, strictly
layer-advancing dependencies, one event per Toffoli, canonical six-PPM event
shape, and resource uniqueness.

All 19 selected OOP/IP widths through 257 pass without materializing a global
pair table. Width-256 OOP/IP now has 34/68 unitless logical candidate levels
for 1,229/2,458 events and 7,374/14,748 PPMs; both constructions meet the
weighted causal lower bound. The 27,184,251/108,744,378 possible global pairs
remain unmaterialized. The largest candidate batch is 765 PPMs; 1,530 is the
combined demand of both ordered phases in one source layer.

Full-ANF OOP/IP widths 5/8 match every compact batch-membership digest and
validate all 2,466 materialized within-batch pairs, Y-free profiles, candidate
counts, and causal bounds. Independent replay imports neither compiler nor
scheduler and rebuilds all 38 certificates. Hash and finite-runtime tampering
fail; malformed axes and non-CSS frame generators return the first
`FALSIFIED` witness and no candidate count. Twenty-five focused and 61 combined
tests pass; the full suite reports 323 passes plus the two known unrelated
sibling-pin failures. Ruff, strict mypy on 54 source files plus the generator,
compileall, and two genuine consecutive byte-identical regenerations of all
six outputs pass.

The result is `PROVED` only inside the architecture-independent logical
screen. It does not supply a code-level simultaneous PPM construction, native
surgery rounds, physical support/placement, routing, source-Clifford or basis-
change duration, reaction/decoder service, factory/buffer service, physical
qubits, or failure probability. All finite outputs remain null. See
`docs/DIRECT_CCZ_QCLA_SCALABLE_COMPATIBILITY_CONTRACT.md`,
`experiments/runs/T-20260903-001/summary.json`, and
`coordination/reviews/T-20260903-001.md`.

The reviewer independently proved the generator-closure theorem itself from
scratch with an explicit numpy matrix construction (X/Z/CNOT/CZ conjugation
preserves the Z-type Pauli subspace across 148 exhaustive test cases on 2- and
3-qubit systems; H breaks it exactly as claimed; any two Z-type Paulis
provably commute; Y-content is automatically impossible) rather than trusting
the docstring, then independently re-derived that the actual OOP/IP source and
event traces satisfy every premise the theorem depends on -- fresh disjoint
resources, the canonical six-PPM shape, CZ/Z/X-only deferred corrections
confined to event data, disjoint source-layer support, strictly
layer-advancing dependencies, and X/CNOT-only passthroughs -- at widths 5, 8,
17, and 256 using a script that imports neither the certifier nor the
compiler. Hand-verified the OOP width-5 within-batch pair count (186) against
the generated summary, and confirmed via `git diff --stat` that this task
touches no previously reviewed compiler, architecture, or batching code.

`T-20260903-002` holds a `REVIEW` lock while Claude reviews the support
certificate. After approval, the next evidence-producing action is to define
one coherent native mapping policy for branch-dependent logical support, or
to prove which frame terms must be materialized before mapping. No subsequent
task is claimed yet.

`T-20260901-010` is `RV-20260901-009` `APPROVED` (Claude review, 2026-09-03).
It adds exact Boolean-ANF anchors at widths 5 and 8, then switches to a compact
source/event traversal for 19 OOP/IP widths through 257 without materializing
quadratic PPM pair tables. The four exact OOP/IP anchors use 12/24 levels at
width 5 and 14/28 at width 8; every construction meets its exact causal lower
bound and contains no fallback PPM.

The direct width-256 structural result has 1,229/2,458 OOP/IP direct-CCZ
events, 7,374/14,748 PPMs, theoretical pair tables of
27,184,251/108,744,378 records, and weighted causal lower bounds 34/68. Both
variants peak at 255 events or 1,530 PPMs in one source layer. Across the 19
selected widths, IP event count, non-Clifford source-layer count, and causal
lower bound are exactly twice OOP; this is labeled `NUMERICAL` for the selected
sweep, not a general proof.

The independent replay imports neither compiler nor scheduler, rebuilds all
38 structural points, and detects mutations to a pair count, exact level, and
prohibited finite runtime. The source two-phase envelope is only `CHECK` and
is not a large-width schedule. Width-256 compatibility remains `OPEN`.
The selected finite gate still has 13 capability gaps, 13 backend gaps, three
incompatible factory fields, and four missing native-mapper obligations, so
all native schedule/time/space/failure outputs remain null. Ten focused tests
pass; the full suite reports 298 passes plus the two known unrelated
sibling-pin failures. See `docs/DIRECT_CCZ_QCLA_SCALING_CONTRACT.md`,
`experiments/runs/T-20260901-010/summary.json`, and
`coordination/reviews/T-20260901-010.md`.

The reviewer confirmed via `git diff --stat` that this task adds one new
module plus purely additive exports and leaves every already-reviewed
compiler/architecture/batching module untouched, independently re-derived
that the weighted-causal-bound rule is a valid general lower bound from the
already-verified two-layer Figure-14(a) event structure (not an empirical fit
at the two anchor widths), and confirmed the analyzer actively cross-validates
this bound against the full exact symbolic causal path at widths 5/8 rather
than only asserting it. A from-scratch verification script importing only the
already-reviewed source-trace builders (never the reviewed scaling module,
compiler, or scheduler) independently reproduced every headline number at
seven widths spanning 5 through 256 using its own independently implemented
longest-path algorithm, including the width-256 figures and the exact
IP-equals-2x-OOP relation at every tested width, and separately confirmed the
power-of-two boundary pattern matches standard parallel-prefix
carry-lookahead theory.

## Reviewed IP-QCLA direct-CCZ foundation

`T-20260901-009` is `RV-20260901-008` `APPROVED` (Claude review, 2026-09-02).
The width-five in-place modulo-QCLA now uses the same
architecture-independent six-PPM direct-CCZ and ordered conditional-Clifford-
frame IR as the reviewed clean OOP trace, without the Selinger seven-T route.
Its 43 source operations map to 20 events, 120 PPMs, 120 conditional updates,
15 pass-through CNOTs, and eight pass-through X gates over 18 source layers,
with all 75 dependencies preserved and no compiler ancilla.

Independent serialized replay imports neither compiler nor scheduler and
checks 1,280 local correction rows, all 43 source frame transitions, 14,880
presented-observable probes, all 1,024 width-five basis inputs, and the local
64-branch injection channel with zero operator residual. Independent batching
replay rebuilds all 120 profiles and 7,140 pair certificates. Exact ANF
compatibility gives a deterministic 24-level construction matching the exact
causal lower bound 24. Seven late-frame profiles exceed exact branch-weight
enumeration: their pair compatibility remains exact, while weight is visibly
reported only as proved lower/upper bounds and distinct-observable count is
null under `A-0037`.

The OOP/IP comparison records 10/20 direct-CCZ events, 12/24 unitless
candidate levels, 36/96 reaction boundaries, and 5/17 explicitly scoped
cleanup operations. Neither count is physical time. Finite execution remains
rejected with 13 capability gaps, 13 backend gaps, three incompatible factory
fields, four native-mapper obligations, and null native schedule/runtime/
physical-qubit/failure outputs. Widths 2--5 pass exhaustive independent source
replay; twelve focused cases, 178 combined related cases, and 288 full-suite
cases pass, with only the two known unrelated sibling-pin failures remaining.
Ruff, strict mypy on 49 library files plus the generator, and byte-identical
two-run regeneration of all 11 artifacts pass. Reviewer findings are in
`coordination/reviews/T-20260901-009.md`; the contract is
`docs/DIRECT_CCZ_IP_QCLA_COMPARISON_CONTRACT.md`.

The reviewer proved by code-structure reading (not just by test) that the OOP
path degenerates byte-for-byte to its pre-existing behavior, independently
re-derived that the new exact-ANF axis-existence test used for profiles above
16 variables is mathematically identical to the brute-force enumeration it
replaces, confirmed the `minimum_weight=1`/support-union `maximum_weight`
bounds are valid proved/conservative bounds (a Clifford conjugate of a
nonidentity Pauli is never the identity), and confirmed the 120-vertex
large-instance conflict-clique shortcut can never corrupt the PROVED-
optimality claim since the causal bound alone already closes it. A from-
scratch verification script that imports none of the reviewed modules ran a
120,000-point Monte Carlo cross-check (400 sampled pairs x 300 random
assignments) against every claimed commutation/axis-conflict/Y decision with
zero contradictions, independently reimplemented the causal DAG longest-path
algorithm from raw JSON and reproduced the 24-level bound exactly, and
hand-verified all combinatorics (7,140 pairs, 336 within-batch, 6,804
cross-level).

`T-20260901-010` consumed these reviewed dependencies and is now
`RV-20260901-009` `APPROVED`.

## Reviewed high-rate-aware QCLA-to-PPM foundation

`T-20260901-008` is `RV-20260901-007` `APPROVED` (Claude review, 2026-09-02).
The deterministic audit atlas regenerates the reviewed Phase-A trace and
Phase-B batching from source, then emits one overview and nine static
macro-layer SVGs. It preserves all 23 source operations, 60 PPMs/outcomes, 60
conditional frame updates, 36 source dependencies, 12 candidate memberships,
and 1,584 cross-level pair certificates; layers 2, 8, and 9 remain visible even
though they contain no PPMs. Every document visibly and mechanically uses
`candidate_batch_level_not_time` and separates the general logical candidate
from the rejected finite backend.

The independent atlas replay imports neither renderer, compiler, nor scheduler.
It rebuilds the displayed projection from serialized inputs, parses all ten
SVGs as XML, and checks one-time SVG coverage of 23 source IDs, 60 PPM IDs, and
60 update IDs. Fourteen focused tests, 52 combined Phase-A/Phase-B/atlas/Hub
tests, Ruff, strict mypy on 49 source files, compileall, and 14-artifact direct
hash determinism pass. Full pytest reports 276 passes plus the same two known
unrelated sibling-pin failures. Manual raster QA caught and fixed palette,
portable-glyph, and frame-out clipping defects before submission. See
`docs/DIRECT_CCZ_PPM_ATLAS_CONTRACT.md` and
`coordination/reviews/T-20260901-008.md`.

This is a `NUMERICAL` audit projection. It adds no native construction,
surgery-round, runtime, physical-qubit, or failure result.

The reviewer independently reconstructed every displayed count from the raw
Phase-A/Phase-B JSON with scripts that import neither the atlas builder nor
the renderer nor the repository's own replay module -- including a
regex-based SVG scan as a genuinely different parse method from the reviewed
module's XML-based one -- and got exact matches throughout (60 PPM-to-batch
memberships, 186 within-batch pairs, 1,584 cross-level certificates with the
full non-exclusive reason tally, and complete 23/60/60/36 source/PPM/
update/dependency coverage). The reviewer also specifically isolated the 378
`deterministic_frontier_partition`-only pairs and confirmed from the raw
relation table (not the doc's prose) that every one is independently marked
compatible, directly substantiating the "not a physical conflict" claim.
Artifacts were regenerated twice with independently-computed byte-identical
hashes, and four structurally distinct panels (overview, densest, PPM-free,
multi-batch) were rasterized and visually inspected with no clipping or
legibility defects found.

`T-20260901-007` is `RV-20260901-006` `APPROVED` (Claude review, 2026-09-01).
The exact Phase-B classifier profiles all 60 presented PPMs and all 1,770
pairs. It finds zero branch-possible-Y PPMs, 30 nonzero symplectic
commutators, 30 per-index axis-conflict pairs, 1,206 causally ordered pairs,
1,116 reaction-connected pairs, and six compatible pairs with shared logical
support. Exact ready-frontier splitting produces 12 unitless candidate levels
of sizes 12, 12, 6, 6, then eight groups of 3. Both the causal-path and
conflict-clique lower bounds are 12, so the construction is optimal only
inside the documented logical candidate model. Peak demand in the stated
semantic-liveness coordinate is 26 logicals/four live CCZ resource states, and
maximum presented PPM weight is seven.

General candidates, finite-instance admission, and low-rate fallback are
separate artifacts. The finite schedule/runtime/physical-qubit/failure fields
are null: 13 capability fields and 13 backend fields remain missing, three
bb18 factory values are incompatible with the selected domain, and four
native-mapper obligations are absent. The low-rate artifact is a 60-PPM
semantic singleton order with finite cost `OPEN`. Measured-product rewrites
and selective Clifford materialization were screened with zero admitted
transforms. The independent verifier imports neither compiler nor scheduler
and reconstructs every relation, dependency/reaction closure, liveness count,
lower bound, output class, and strategy row from serialized dictionaries. See
`docs/DIRECT_CCZ_PPM_BATCHING_CONTRACT.md` and
`coordination/reviews/T-20260901-007.md`.

The reviewer independently reimplemented the entire DAG-closure and relation
model from scratch, matching every claimed count exactly after catching and
fixing a bug in the reviewer's own first attempt (a nominal-support-vs.
frame-corrected-presented-support mismatch in the compatible-pair count),
independently re-validated the actual 12-level schedule end to end with zero
compatibility or causality violations found, and independently re-derived the
peak liveness figures from the contract's stated rule.

The number 12 is not surgery depth, a duration, or a finite-backend schedule.

`T-20260901-006` is `RV-20260901-005` `APPROVED` (Claude review, 2026-09-01).
The reviewed OOP-QCLA `n=5` source now lowers directly, without seven-T
decomposition, through the exact `|CCZ>` injection event into a canonical
symbolic PPM/frame trace. The 23 source operations produce ten injections, 60
PPMs, 60 conditional frame updates, and thirteen implementation-neutral CNOTs
while preserving 36 source dependencies, sixteen source logical lifetimes, ten
CCZ resource lifetimes, and zero compiler ancillas. The independent serialized
replay checks 640 local correction rows, 23 frame transitions, 3,840 presented
observables on 64 deterministic global probes, all 1,024 basis inputs, and the
all-64-branch local injection channel with zero operator residual. The
reviewer independently verified every primitive Clifford-conjugation rule
(H/X/Z/CNOT/CZ) against explicit unitary matrices, recognized the CNOT phase
formula as the textbook Aaronson-Gottesman stabilizer sign-update rule, and
performed an independent end-to-end reconstruction of a nontrivial later
PPM's presented observable -- catching and fixing a bug in the reviewer's own
first attempt (a missed passthrough-CNOT frame-reconjugation replay step)
before confirming an exact match with the compiler's stored output. See
`docs/DIRECT_CCZ_PPM_TRACE_CONTRACT.md` and
`coordination/reviews/T-20260901-006.md` for the complete finding list.

This is a `NUMERICAL` semantic trace, not a native schedule or formal proof.
The global probes are not exhaustive `2^60` enumeration, source layers are not
surgery rounds, and pass-through CNOT time/space/routing/memory costs remain
`OPEN`. Both compiler and replay reject `complete_native_schedule=true`; no
`schedule.json` was emitted.

`T-20260901-008` renders the reviewed decisions from the same machine-readable
trace and candidate artifacts and is `RV-20260901-007` `APPROVED`.
`T-20260901-009` reuses the compiler for IP-QCLA without the existing seven-T
route and is `RV-20260901-008` `APPROVED`.
`T-20260901-010` now separates exact-anchor width scaling from the still-open
compatible finite-backend integration and is `RV-20260901-009` `APPROVED`.

The cycle contract is
`docs/HIGH_RATE_QCLA_PPM_OPTIMIZATION_CYCLE.md`. It explicitly forbids
treating source Toffoli layers, pairwise commutation, logical-axis consistency,
or noiseless Gross-code observations as an executable high-rate runtime.
Runtime additionally requires memory, routing, reaction, decoder, CCZ
factory/buffer, physical-space, and failure-budget fields from one compatible
backend.

## Current objective

`T-20260901-001` is `RV-20260901-001` `APPROVED` (Claude review, 2026-09-01).
Gidney--Fowler Figures 3--6 plus the official layouts connect one CCZ factory
output to a three-delayed-CZ AutoCCZ fixup box and one Toffoli consumer in a
single surface-code domain. An independent abstract channel check finds all 64
branches at probability `1/64`, maximum probability error
`2.2551405187698492e-17`, and zero ideal-CCX operator residual. The adapter is
admitted, but complete service remains false: nine finite fields are missing,
and the official `5.33332e-11` calculator error belongs to `d1=15,d2=31`, not
the selected AutoCCZ `d1=17,d2=27` example. Under explicitly `CHECK` timing
inputs, the latter yields 135 cycles/CCZ, approximately 7.407 kHz per factory,
and fourteen factories for 100 kHz average demand. No schedule was emitted.
The reviewer rendered the primary PDF's Figures 3, 4, and 6 directly at 300
DPI and confirmed the delayed-choice-cell abstraction, three-cell/six-routing
-qubit structure, and one-port consumer interface are faithfully transcribed,
with `pdftotext` independently matching the paper's own worked-example
arithmetic word-for-word; separately unzipped and parsed the official ODS
calculator's raw XML and found the `5.33332e-11` cell's own formula is in the
same column as `d1=15`, with `d1=17` never appearing anywhere in the sheet --
directly and independently settling the calculator-incompatibility claim from
the spreadsheet's own structure rather than the doc's description of it. See
`coordination/reviews/T-20260901-001.md` for the complete finding list.

`T-20260831-004` is `RV-20260831-004` `APPROVED` (Claude review, 2026-08-31).
The fail-closed audit covers 17 required direct-CCZ fields and screens seven
pinned primary sources without composing incompatible code families. The
selected Cain ECC-256 `P=20` time-efficient candidate is rejected: 13 finite
service fields remain absent, while the only qualified factory batch size,
production time, and output-error values belong to the separate `bb18`
space/balanced domain. The portable Figure 14(a) event remains admitted. No
schedule artifact was emitted. The reviewer independently re-hashed all seven
source PDFs, confirmed the `_PORTABLE_FIELD_IDS` exemption is a hardcoded
Python constant rather than a YAML-editable field, ran every boundary test
(forged admission, omitted field, coherent synthetic admission, mixed-domain
rejection, real-candidate rejection), and -- most importantly -- pulled the
raw Cain PDF text at pages 19 and 24 and found the source itself states the
10-CCZ/120-cycle/`1e-10` figures apply "in our space-efficient or balanced
architecture" (a different regime from the selected `P=20` time-efficient
candidate) and that the time-efficient appendix explicitly disclaims
specifying "concrete circuits or instruction sets." See
`docs/DIRECT_CCZ_FINITE_BACKEND_AUDIT.md`,
`configs/architectures/direct_ccz_finite_backend_audit_v1.yaml`,
`experiments/runs/T-20260831-004/summary.json`, and
`coordination/reviews/T-20260831-004.md` for the complete finding list.

`T-20260831-003` implementation commit `75effd5` is `RV-20260831-003`
`APPROVED` (Claude review, 2026-08-31). Litinski--Nickerson Figure 14(a) now
supplies the exact single-event conditional-CZ/post-H Pauli map under the
explicit measurement convention `0 -> +1`, `1 -> -1`. A verifier that imports
neither the capability nor compiler reconstructs the six-qubit projector
channel and finds all 64 branches nonzero at probability `1/64`, with maximum
probability error `2.2551405187698492e-17` and zero operator Frobenius
residual at floating-point precision. The real capability therefore admits
isolated event lowering. The reviewer independently confirmed this by
rendering the primary source PDF page to a 600 DPI image and directly
pixel-verifying every wire assignment, conditional-CZ pairing, and final
Pauli-correction formula in Figure 14(a) against the machine-encoded map
(zero discrepancies), and by writing a separate from-scratch numpy channel
reconstruction from the contract's prose alone (before reading the
repository's own verifier), which independently reproduced all 64 nonzero
branches at matching precision; see `coordination/reviews/T-20260831-003.md`
for the complete finding list.

The width-256 clean OOP-QCLA lowers to 1,229 direct-CCZ injection events,
7,374 PPM/outcome records, 3,955 preserved source dependencies, and 766
pass-through CNOTs. Event-trace schema v2 explicitly remains
`complete_native_schedule=false`. High-rate admission remains false: finite
timing, error, decoder, reaction, port, capacity, routing, factory delivery,
buffer, and storage evidence is still absent. No runtime or physical-resource
result was created.

`T-20260831-002` completed the first bounded cycle proposed by the reviewed
direct-CCZ plan. It generated and replay-validated a clean out-of-place
modulo-\(2^{256}\) QCLA trace with 1,229 Toffolis, 766 CNOTs, 20 source layers,
240 clean prefix-scratch values, and 1,008 fully resident source values. These
are architecture-neutral circuit quantities, not runtime.

The same cycle audited the pinned direct-CCZ and high-rate sources into a
machine-readable capability record. The sources establish a six-PPM
single-injection skeleton and a separate ten-CCZ/120-cycle factory observation,
but not the exact outcome-to-correction map or a finite high-rate direct-CCZ
backend. The adapter therefore rejects before emitting any source-qualified
event. Implementation commit `deebfc4` is `RV-20260831-002` `APPROVED`
(Claude review, 2026-08-31). The reviewer wrote an independent from-scratch
classical-reversible simulator (bypassing the repository's own
`replay_oop_qcla`) and confirmed every closed-form count and the fail-closed
capability/adapter logic; see `coordination/reviews/T-20260831-002.md` for
the complete finding list. The `OPEN` capability conclusion itself is
unchanged by the review -- the exact correction map and finite high-rate
backend remain absent from the literature.

`T-20260825-002` converted the reviewed width-256 QCLA adaptive-PBC trace from
a resident-capacity rejection into an independently replayed, fixed-order
60-slot J300 memory schedule. The width-256 ten-scratch high-rate policy
selects 1,576 exact-ten-XX batches. Under the explicitly `CHECK`
one-lane/one-round/no-overlap profile it takes 2,420,527 rounds, 169,260
(6.54%) below one-scratch serial despite 7,433 more reloads. This is not
executable time. The complete shifted T-demand trace sums to 17,206 but has
no factory service, buffer, routing, or stalls.

## Incoming-collaborator orientation

`T-20260901-004` is `RV-20260901-003` `APPROVED` (Claude review, 2026-09-01).
`docs/HANDOFF.md` is a concise English entry note for an incoming
collaborator. It presents the one-week/order-`10^4`-qubit research target,
summarizes the teleportation-ripple HGP and QCLA/high-rate-surgery tracks,
lists their open physical-contract questions, and links scoped starting
references. It creates no numerical result or executable architecture claim.
The reviewer independently verified all ten citations against arXiv and the
local bibliography with no discrepancies found.

`T-20260901-003` is `RV-20260901-002` `APPROVED` (Claude review, 2026-09-01).
The two human-audit OOP-QCLA `n=5` figures (source circuit and direct-CCZ
injection expansion) live outside the git repository in a thread-owned
visualization cache; see `coordination/reviews/T-20260901-003.md` for their
path. The reviewer independently regenerated the width-5 trace and matched
all 23 gates and the displayed correction formula exactly.

## Read first

- `context/PROJECT_CHARTER.md`
- `Research Hub/Home.md`
- `context/STATUS.md`
- `context/TASKS.md`
- `coordination/PROTOCOL.md`
- `coordination/reviews/T-20260901-001.md`
- `docs/AUTOCCZ_SURFACE_CODE_ADAPTER.md`
- `configs/architectures/autoccz_surface_code_adapter_v1.yaml`
- `experiments/runs/T-20260901-001/summary.json`
- `experiments/runs/T-20260901-001/autoccz_service_audit.json`
- `experiments/runs/T-20260901-001/autoccz_channel_verification.json`
- `coordination/reviews/T-20260831-003.md`
- `docs/DIRECT_CCZ_SINGLE_EVENT_CONTRACT.md`
- `configs/architectures/direct_ccz_single_event_capability_v1.yaml`
- `experiments/runs/T-20260831-003/summary.json`
- `experiments/runs/T-20260831-003/direct_ccz_injection_channel_verification.json`
- `coordination/reviews/T-20260831-002.md`
- `docs/DIRECT_CCZ_CAPABILITY_AND_OOP_QCLA_CONTRACT.md`
- `configs/architectures/direct_ccz_high_rate_capability_v1.yaml`
- `experiments/runs/T-20260831-002/summary.json`
- `experiments/runs/T-20260831-002/direct_ccz_capability_gap.json`
- `coordination/reviews/T-20260825-002.md`
- `docs/QCLA_MEMORY_IO_CONTRACT.md`
- `docs/QCLA_PBC_LOWERING_CONTRACT.md`
- `configs/architectures/qcla_j300_memory_io_v1.yaml`
- `experiments/runs/T-20260825-002/summary.json`
- `experiments/runs/T-20260825-002/qcla_width256_t_state_demand.json`
- `context/RESULT_LEDGER.md`
- `docs/HIGH_RATE_QCLA_DIRECT_CCZ_RESEARCH_CYCLE.md`
- `coordination/reviews/T-20260831-001.md`

## Next concrete action

0. `T-20260906-004` (OOP, 15/30), `T-20260907-001` (IP, 30/60), and
   `T-20260907-002` (the shared OOP/IP branch-weight distribution overlay)
   are all approved. Both width-256 commutation-aware structural results are
   now certified, with the IP support envelope explicitly `CHECK` (31 of 60
   levels exact, 29 sampled/may-support) rather than fully resolved, and the
   branch-weight overlay adds distributional witnesses (p50/p95/p99, hashed
   maxima) beside those ceilings without changing either schedule. No task
   ID is claimed yet for the next step: implement one coherent native mapper
   or explicit frame-materialization policy for these certified logical
   candidate levels and the branch-dependent support hypergraphs from
   `T-20260903-002`, together with a mixed-axis-compatible cleanup protocol
   (frame clearing, a mixed-axis PPM construction, or a new joint cleanup
   protocol) if OOP cleanup is ever to be revisited, and/or a plan to close
   the IP support envelope's remaining 29 `CHECK` levels before treating it
   as exact.
1. Source or compute a `d1=17,d2=27` output/transport/consumer
   error model and a finite decoded buffer/reaction contract before connecting
   the AutoCCZ adapter to width-256 QCLA demand.
2. Add factory service, finite buffer, routing, and backlog to the width-256
   adaptive-PBC T-demand series as a separate, comparison track; report stalls
   separately from the current ideal-supply timeline.
3. Implement one coherent native mapper and finite backend that can admit the
   now-certified 34/68 width-256 logical candidate levels from
   `T-20260903-001`, together with the branch-dependent support hypergraphs
   from `T-20260903-002` (either a mapper that handles branch-dependent
   support directly, or an explicit frame-materialization policy). Do not
   treat those levels as surgery rounds while physical support, routing,
   timing, capacity, decoder/reaction, and factory service are open; no task
   ID is claimed for this yet.
4. Human records the `T-BOOT-001` full-ECDLP circuit choice before project-wide
   `T-BOOT-002` is claimed.

## Known risks

- `R-20260901-005` proves 12-level optimality only inside the explicit logical
  candidate model. Bounded-degree construction, distance preservation,
  physical support, routing, decoder service, and finite capacity are `OPEN`;
  no reviewer should relabel candidate levels as surgery rounds.
- The six compatible overlapping pairs establish that overlap alone is not a
  conflict under the screen; they do not establish a backend construction for
  overlapping physical supports.
- Product rewrites and selective frame materialization have zero admitted
  transforms. Their screened counts are opportunities, not validated savings.
- The logical peak of 26 uses the documented semantic-layer/just-in-time-clean
  coordinate; it is neither a physical-qubit total nor a finite memory plan.
- `R-20260901-003` preserves exact ANF conditions, but its 64 global outcome
  probes are a regression set rather than exhaustive `2^60` branch coverage.
  The local injection itself remains all-64-branch checked.
- Assumption `A-0035` propagates source CNOTs semantically as materialized
  Clifford frames and assigns no finite native cost. Phase B must not turn
  these frame records into zero-time physical operations.
- `R-20260901-001` is an abstract logical-channel reconstruction whose
  delayed-choice CZ cells are accepted from the paper; it does not simulate
  surface-code faults or independently validate the 3D layout.
- `R-20260901-002` uses source-stated cycle/reaction inputs as `CHECK`; average
  throughput and fourteen-factory arithmetic do not prove burst service.
- The official workbook's finite output error is deliberately incompatible
  with the selected distances. Substituting it would create a false closed
  failure budget.
- `R-20260831-006` is an `OPEN` negative admission result. Its field counts are
  deterministic, but they do not prove that no finite direct-CCZ backend can
  exist; they prove only that the pinned corpus does not close the selected
  candidate under the recorded compatibility rule.
- Tricycle finite CCZ generation strengthens the factory side but leaves
  selective initialization and target-code teleportation unresolved; the
  reported low memory error does not include the CCZ circuit's contribution to
  final magic-state fidelity.
- The clean QCLA source-ancilla allocation/release boundaries are validated
  from source reuse epochs, but their physical preparation/reset/routing time
  remains `CHECK` and adds no separate duration in this cycle.
- The capacity-relaxed adaptive-PBC pass selects an order only. The second pass
  enforces 60 slots, but the order and Belady retention are heuristic and are
  neither optimal nor lower bounds.
- Transfer prefetch/overlap, finite memory capacity, routing, bridge occupancy,
  decoder throughput, logical failure, and wall-clock conversion are absent.
- The QCLA is uncontrolled in-place addition modulo `2^n`, without carry-in or
  overflow; it is not yet the controlled arithmetic needed by scalar
  multiplication.
- Direct CCZ injection may dominate the seven-T baseline in space or time.
- The high-rate source presently supports a finite XX PPM demonstration, not an admitted direct-CCZ batch; this is an explicit input gap, not a scaling assumption.
- The clean OOP trace is validated on computational-basis replay and structural identities; it is not an independent coherent-phase proof of the full arithmetic circuit.
- The legacy T-20260831-002 capability record intentionally remains null and fail-closed. Only the new Figure-14-qualified configuration admits isolated events.
- The branch reconstruction is `NUMERICAL`, not a formal proof, and it does not establish any finite high-rate architecture.
- Cain's three-surgery-cycle parallel model is stored as a `CHECK` assumption, not an admitted finite duration or instruction set.
- The older Gidney integration suite retains two known checkout-pin failures:
  expected sibling HEAD `8c16388`, observed `75a6e83`. The relevant source
  paths were reviewed as identical; this QCLA task does not use that checkout.

## Files currently safe to modify

No task currently holds an active lock in `coordination/WORK_LOCKS.md`; every
row is `RELEASED`.
