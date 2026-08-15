# Open questions

| ID | Priority | Layer | Question | Blocking tasks | Proposed next action |
|---|---:|---|---|---|---|
| Q-0001 | 0 | algorithm | Which ECDLP-256 circuit is the canonical first baseline? | T-BOOT-001 | Compare reproducibility, width, gate count, and available source code |
| Q-0002 | 0 | architecture | Which sequential PPM architecture should be reproduced first? | T-BOOT-003 | Record exact timing and code assumptions from one reference |
| Q-0003 | 1 | factory | What resource state should be canonical: T, CCZ, or mixed? | T-BOOT-006 | Derive demand traces for the chosen circuit |
| Q-0004 | 1 | scheduler | Which parallel-surgery constraints are necessary beyond a scalar width limit? | T-BOOT-004 | Encode conflict graphs or supported measurement families |