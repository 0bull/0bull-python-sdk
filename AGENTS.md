# 0bull Python SDK

Python client for the 0bull API.

- Product: https://0bull.net
- API docs: https://docs.0bull.net

The API docs are the contract. When they are unclear or contradict observed API behavior, stop and ask.

Stack, commands, and project layout are defined in `SPEC.md` once it is approved. Until then, do not pick them silently.

## Process

Every change goes through the agent-skills lifecycle. Check for the applicable skill before starting work, and follow its steps in order, including verification.

| Phase | Skill | Output |
|---|---|---|
| Clarify | `interview-me`, `idea-refine` | Agreed intent |
| Define | `spec-driven-development` | `SPEC.md`, approved by the user |
| Plan | `planning-and-task-breakdown` | `tasks/plan.md`, `tasks/todo.md` |
| Build | `incremental-implementation` + `test-driven-development` | One thin, tested slice at a time |
| Build | `api-and-interface-design`, `source-driven-development` | Public API checked against the API docs |
| Review | `code-review-and-quality`, `code-simplification`, `security-and-hardening` | Findings fixed |
| Ship | `git-workflow-and-versioning`, `documentation-and-adrs`, `shipping-and-launch` | Clean history, docs, release |

- No code without an approved spec and plan. Small fixes still need a failing test first (`debugging-and-error-recovery` → `test-driven-development`).
- Surface assumptions before non-trivial work. When confused, stop and ask.
- A task is done only when its acceptance criteria are met and, with evidence shown: new behavior has tests that fail without it, the full suite, lint, and type checks pass, public API changes are documented, and the user has reviewed it.
- Never overwrite `tasks/plan.md` or `tasks/todo.md` while they still have unchecked tasks for other work.

Before opening a PR:

1. Open Code Review in delegation mode (no OCR model is configured): `ocr delegate preview --from main --to HEAD` for the files, `ocr delegate rule <files>` for the rules, then review against them and fix real findings.
2. `anti-ai-slop` over the branch.

## Clean code

- Simplest thing that works: stdlib first, then an existing dependency, then new code. New dependencies need a reason in the PR.
- Names reveal intent. Comments explain why, never what.
- No dead code, debug output, commented-out blocks, or speculative abstractions.
- Scope discipline: touch only what the task needs. No drive-by refactors.
- Public API is typed, documented, and stable. Breaking it requires a major version bump.
- Validate at trust boundaries: API responses, user input, config. Never log or commit secrets or tokens.
- Never weaken a check to get green: no skipped tests, removed assertions, or new lint/type suppressions without a stated reason.

## Git

- Branch per change off `main`, named `<type>/<short-description>`. Keep branches short-lived.
- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/): `<type>(<scope>): <description>`
  - Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`
  - Lowercase imperative description, no trailing period, header ≤ 72 chars
  - Body explains why. Breaking changes use `!` after the type and a `BREAKING CHANGE:` footer
- Atomic commits: one logical change each, tests passing at every commit. Never mix refactors with behavior changes.
- Commit, push, or open PRs only when the user asks.
