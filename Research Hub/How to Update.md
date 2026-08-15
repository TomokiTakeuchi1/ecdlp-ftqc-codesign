---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - maintenance
updated: 2026-08-15
---

# How to Update This Hub

[[Research Hub/Home|← Home]]

## Five-minute update

1. Update the canonical task, result, decision, assumption, or review record first.
2. Add one plain-language dated entry to [[Research Hub/Progress Log|Progress Log]].
3. Refresh the status table and “Next three decisions/actions” in [[Research Hub/Home|Home]].
4. If a blocker or human choice changed, update [[Research Hub/Decisions and Blockers|Decisions & Blockers]].
5. Run `pytest tests/unit/test_obsidian_hub.py` to catch broken navigation or malformed Canvas data.

## Source-of-truth rule

The Research Hub is intentionally a manually curated presentation layer. Its job is to make the project understandable in under five minutes. It does not replace:

- [[context/STATUS|Project Status]] for project-level state;
- [[context/TASKS|Task Board]] for work ownership;
- [[context/RESULT_LEDGER|Result Ledger]] for reproducible numerical claims;
- [[context/DECISIONS|Decision Log]] and [[context/ASSUMPTIONS|Assumptions]] for durable modelling choices;
- [[coordination/REVIEW_QUEUE|Review Queue]] for acceptance state.

Generated experiment outputs must never be manually edited. Change the source/configuration and regenerate them.

## Writing style

- Lead with what changed and why it matters.
- Name the status: **Reviewed**, **In review**, **Human decision**, **CHECK**, or **Not started**.
- Put precise counts beside their exclusions and assumptions.
- Link to the canonical evidence rather than duplicating long technical detail.
- Never translate algorithmic critical-path depth directly into an executable runtime.
