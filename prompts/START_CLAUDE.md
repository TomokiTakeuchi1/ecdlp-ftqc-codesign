Read `CLAUDE.md` and its imported project context. Act as owner `claude`.

First inspect `coordination/REVIEW_QUEUE.md`. Review pending Codex work before claiming a new implementation task unless the human priority explicitly says otherwise. Then inspect `context/TASKS.md` and `coordination/WORK_LOCKS.md`.

Do not edit files until you have selected one unclaimed task, recorded the claim, listed the intended files, and created a session record. Make the smallest change that satisfies the acceptance criterion. Run tests, document assumptions and limitations, update the handoff, release the lock, and request Codex review for nontrivial changes.