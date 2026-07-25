# Next Steps

Implementation order (final review): Schema → Event Store → Evaluation →
Knowledge → Runtime. Experience layer and frontend come LAST, only after the
four foundations are un-bypassable engineering constraints.

## Done (Phase 0 gates)

1. **Schema contracts** — `runtime/contracts.py` validates every boundary
   object (GrowthPlan, MissionArc, evidence signals, ParentInsight);
   violations hard-fail.
2. **Event Store** — growth state AND runtime state (active mission, chapter
   progress) replay from the event log; snapshots are checkpoints only.
3. **Safety** — Input Guard enforced inside `EventStore.append` (PII cannot
   reach the log); Output Guard reviews all human-facing arc fields,
   rationale, and insights; red-line suite in `evaluation/red-line.yaml`.
4. **Evaluation** — 22-case golden set, gates pass offline
   (`python -m evaluation.runner --mock`); four-virtual-children acceptance
   tests in `tests/test_evaluation.py`.
5. **Runtime** — derived capability view (ADR-004 formula) feeds the Planner;
   Growth Memory penalizes failed arcs; minimal Parent Coach closes the
   family loop.

## Remaining

1. **Expert adjudication gate** — capability taxonomy + topic→capability map
   are draft/mock; formal runtime rejects mock maps by default. Run
   `build_mapping --live`, human-review the spot-check sample, then re-version.
2. **i18n coverage** — only the starter topic set has polished zh; untranslated
   topics fall back to English in parent-facing checklists. Translate or
   exclude from the demo surface.
3. **Provenance** — pin os-taxonomy as a real submodule so knowledge versions
   rebuild deterministically from the repo alone.
4. **Experience layer / frontend** — only after 1-3.
