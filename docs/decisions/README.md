# Decision Log (ADR-lite) — SHARED memory for every agent

This directory holds **cross-cutting decisions** that *multiple* agents must follow to
avoid clashing on conventions: interfaces in shared modules, naming conventions, choice of
library/pattern, architectural boundaries.

## Why it's needed

The registry holds *task-context* (narrow, for one task). `docs/decisions/` holds
*project-context* (broad, for every task). Many parallel agents can make decisions that
are **locally correct but globally inconsistent** — two naming styles, two interfaces that
don't line up at a shared boundary. ADRs turn those decisions into a **re-readable
artifact**, instead of living in one agent's head or in chat history that gets lost.

## Rules for agents (MANDATORY)

1. **Before** making a decision that affects multiple modules / a shared boundary: READ
   this directory. If a decision already exists here, FOLLOW it — don't choose otherwise.
2. If you need a NEW cross-cutting decision (no ADR yet): **STOP, propose an ADR** in the
   PR/issue — don't decide silently in a feature branch. A shared decision must go through
   a control-plane PR (an `ops/*` branch) approved by a CODEOWNER, then features build on it.
3. Reference the ADR in `task.log` and the PR description (e.g. "per ADR-0002").

## How to write an ADR

- Copy `TEMPLATE.md` to `NNNN-short-title.md` (increasing number, 4 digits).
- Fill in: Status, Context, Decision, Consequences. Keep it short — one screen is enough.
- An ADR is **immutable once Accepted**: to change it, write a new ADR that `Supersedes NNNN`,
  and mark the old one `Superseded by MMMM`. Don't rewrite decision history.

## Index

- [0001](0001-record-architecture-decisions.md) — Use ADRs to record architecture decisions.
