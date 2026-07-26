# ADR-021: Content OS — Content Is the Moat

- Status: Accepted
- Date: 2026-07-26
- Supersedes: Engineering-Spec v1.1 ADR-007 (renumbered)

## Context

For a solo developer with AI workers, the durable asset is not code — it is
the content model of child growth: who Doudou is, what good adventures look
like, which prompts produce them.

## Decision

Content lives as versioned, contract-validated data, separate from code:

- `content/doudou-bible.yaml` — Character Bible (character-bible contract).
- `world-model/growth-patterns.yaml` — 5 growth patterns (growth-pattern contract).
- `world-model/adventure-templates.yaml` — 10 adventure skeletons
  (adventure-template contract).
- `prompts/*_v*.md` — Prompt OS, versioned; the active version is recorded
  in every decision trace.
- World Bible and Asset Library: pending (Phase 0 assets arrive as real
  files under assets/ with semantic refs).

All content validates against its schema at load; unvalidated content
cannot reach runtime.

## Consequences

- Content edits are data PRs with contract tests, no code deploy needed.
- AI may personalize instances; it may not edit these sources at runtime.
