# 0001 — Workflow

1. Read `AGENTS_START_HERE.md` and relevant `.plan/` docs.
2. Prefer TDD: failing test → implementation → green → refactor.
3. Verify on **app-test-001** (`172.16.176.133`) with `python3.12 -m pytest`.
4. Same-PR documentation for user-visible behavior changes.
5. Storage invariant: never write finished media to CWD.
