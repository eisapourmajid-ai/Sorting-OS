# جریان کار توسعه GitHub

1. Main is the protected source-of-truth branch.
2. Create a feature branch from latest main; do not push experimental code directly to main.
3. Every prompt produces a bounded commit, report and test evidence.
4. PR title references module and intent; description includes requirement IDs, migration, risk, test commands and known limitations.
5. Review source diff and generated files. Never include real customer/financial data, SQLite DBs, CSV exports, secrets, or private keys.
6. CI checks compile/tests/lint/docs. If CI cannot test Windows 7, mark that target unverified and retain manual OS test evidence as a release gate.
7. Merge only after tests and gate review. Release tagging and artifact release occur after handover prompt 35.
