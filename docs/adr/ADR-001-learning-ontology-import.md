# ADR-001: Learning Ontology Import (os-taxonomy)

- Status: Accepted
- Date: 2026-07-24

## Context

AI Growth OS needs a skill/knowledge graph for ages 4-6 (MVP), extensible to
7-12+. Building one from scratch was estimated at 2-3 weeks with high risk of
developmentally-wrong prerequisite ordering.

The Marble Skill Taxonomy (`../os-taxonomy`, v1) provides 1,590 micro-topics,
3,221 prerequisite edges (DAG), per-topic mastery evidence criteria,
assessment prompts, and curriculum alignment. 426 topics overlap ages 4-6.

License: ODbL 1.0 (database) + CC BY-SA 4.0 (authored content). Product use is
permitted; derivative *databases* must remain open; attribution required.

## Decision

1. Adopt os-taxonomy as the **Learning Ontology** of AI Growth OS.
2. Integrate as a **git submodule pinned at v1** + an import pipeline
   (`import_taxonomy`) that filters the age 4-6 subset, applies capability
   mapping, and emits AI Growth OS's own derived knowledge-base files.
3. Hand-authored additions (Physical Development, Executive Function,
   Creativity topics) live in **separate files** under the same schema; the
   pipeline merges them. This keeps provenance and share-alike obligations
   clean.
4. **Upstream immutable, local artifacts versioned.** The submodule is never
   modified; each import emits a versioned artifact
   (`os-taxonomy v1 → growth-artifact v0.1`). Re-running the pipeline against
   a new upstream tag is the upgrade path.

## Consequences

- Planner operates on a real prerequisite graph instead of LLM-invented
  ordering.
- Upstream bugfixes and 7-12 coverage arrive by re-pinning the submodule.
- Attribution notices must ship with any distributed artifact.
