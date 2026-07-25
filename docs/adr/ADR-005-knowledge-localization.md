# ADR-005: Knowledge Localization Strategy

- Status: Accepted
- Date: 2026-07-24

## Context

The Learning Ontology (ADR-001) is English; the product serves Chinese
families. Translation timing and placement directly shape the data pipeline:
what gets translated, when, and where the translations live.

## Decision

1. **Source knowledge is never translated, never modified.** os-taxonomy
   stays byte-identical (submodule pin). All localization is additive.
2. **Independent i18n layer**: `i18n/zh-CN.yaml` keyed by stable ids
   (`mt_...` for topics, capability ids). Same file discipline as the
   capability mapping (ADR-004) — our data, our evolution, clean provenance.
3. **Phase 0 scope**: basic Chinese semantics for all Topics and Capabilities
   in the 4-6 subset (LLM-translated, spot-checked).
4. **Evidence criteria get priority human polish.** `evidence` text becomes
   the parent-facing observation checklist — the fulcrum of evidence quality
   (ADR-002). This is the one field where translation quality is
   load-bearing.
5. **Canonical knowledge stays English; runtime prompt language is chosen
   per model capability and task** — not locked to English. Source wording
   (description, assessmentPrompt) is curriculum-aligned and translation is
   lossy, so the canonical store never translates. A future Chinese-native
   agent may warrant Chinese prompts; that choice belongs to the runtime,
   not the knowledge base.
6. **Future: China Child Growth Adaptation Layer** (中国儿童成长适配层) —
   cultural/developmental adaptation for Chinese family context (activity
   patterns, examples, holiday/school rhythms), as a separate overlay file,
   not edits to source or i18n.

## Consequences

- The pipeline has a fixed layering: source (frozen) → mapping (ours) →
  i18n (ours) → adaptation overlay (ours, later) → merged runtime artifact.
- Translation debt is explicit and localized: exactly one field class
  (evidence criteria) requires human-grade Chinese in Phase 0.
