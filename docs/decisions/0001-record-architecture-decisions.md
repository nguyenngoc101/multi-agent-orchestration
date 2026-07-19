# 0001 — Use ADRs to record architecture decisions

- **Status:** Accepted
- **Date:** 2026-07-19
- **Deciders:** CODEOWNER (@nguyenngoc101)

## Context

Many agents (Claude/Codex/other) work in parallel on the same repo. Each has its own
context window, ephemeral and quickly divergent. If a cross-cutting decision (shared
interface, convention) lives only in one agent's head or in chat history, the other agents
don't see it → they make inconsistent decisions and integration breaks at shared boundaries
that file-scope CI can't catch (each PR is within its own scope, but combined they don't fit).

## Decision

Every **cross-cutting** decision is recorded as an ADR in `docs/decisions/`, numbered
increasingly, immutable once Accepted. Agents MUST read this directory before making a
decision that affects multiple modules, and must not choose against an Accepted ADR. A new
ADR goes through a control-plane PR (`ops/*`) approved by a CODEOWNER.

## Consequences

- (+) Project-context is reconstructable from an artifact, not dependent on agent memory.
- (+) Coherence across parallel tasks no longer relies solely on a reviewer catching drift.
- (−) One extra step: a shared decision must be written down + approved before features build
  on it. This is a deliberate cost — traded for consistency when many agents are involved.
- A boundary settled in an ADR is the "merged truth" that other tasks build on; an interface
  in a shared module should be a prerequisite task (`depends_on`), not defined by two agents
  in parallel.
