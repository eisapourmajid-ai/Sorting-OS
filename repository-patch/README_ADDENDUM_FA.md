# افزوده README مخزن

## Desktop application status
A coded desktop MVP now lives in `desktop/`. Read `desktop/README_FA.md` for local execution and current limitations. The MVP is not yet production accounting software and Windows 7 compatibility has not been verified.

## AI agent sequence
Use `docs/agent-prompts/MASTER_PROMPT_FOR_AGENT_FA.md` first and then execute exactly one prompt from `docs/agent-prompts/PROMPT_INDEX_00_TO_35_FA.md` per iteration. Do not execute all prompts in a single pass. Prompt 00 is read-only repository audit.

## Release safety
Never merge a desktop feature to `main` without a reviewed PR, passing relevant tests, validated migration, backup/restore evidence, and a release gate report. A draft PR is not a release.
