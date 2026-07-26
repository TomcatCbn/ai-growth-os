# ADR-017: AI Composition Model

- Status: Accepted
- Date: 2026-07-26
- Supersedes: Engineering-Spec v1.1 ADR-003 (renumbered)

## Context

"AI 不负责创造一个新角色，而负责让同一个豆豆兔每天经历新的故事。"
Fully AI-generated content drifts (character, tone, safety) and is slow;
fully static content can't personalize.

## Decision

Fixed assets + AI personalization. AI creates: dialogue, story adaptation,
personalization, reasoning. AI never changes: character identity (Character
Bible, content/doudou-bible.yaml), world rules, core growth goals, or the
shape of the child-facing flow. Asset references are semantic
("character/doudou/emotion/happy"), never file names — an Asset Composer
resolves them.

## Consequences

- Character Bible and Growth Patterns/Templates are versioned data,
  contract-validated at load.
- AI video stays out of the main loop (special moments only).
