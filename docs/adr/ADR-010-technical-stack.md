# ADR-010: Technical Stack & Platform Modules

- Status: Accepted
- Date: 2026-07-25

## Decision

| Module | Choice |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Agent Runtime | Self-built lightweight runtime; NO LangGraph for v1 (linear pipeline, ADR-006's three triggers) |
| LLM | Provider-agnostic client abstraction, Claude default (Sonnet: extraction/generation; Opus: Planner decisions) |
| Agent Output | JSON Schema contracts + Pydantic validation on every LLM response |
| Storage | SQLite + append-only Event Store + snapshots; Alembic/versioned SQL for migrations, no self-built ORM tooling |
| Frontend (demo) | FastAPI SSR (Jinja2 + minimal JS), single page; no child-facing client |
| Knowledge | Build-pipeline artifact (submodule input → merged versioned output, ADR-001/005) |
| Schema | JSON Schema is the single source of truth; pydantic models codegen'd |

## Two first-class platform modules

### Evaluation (一等模块)

Evaluation is infrastructure, not a test folder. It owns: the extraction
golden set (Q12), the safety red-line set (ADR-008 Layer 2), frontier
legality checks (ADR-003), rule-vs-LLM planner A/B harness (ADR-003), and
later multi-model comparison. Every prompt/model/pipeline change runs it.

### Decision Trace (一等模块)

Every LLM judgment call (frontier ranking, mission generation, modality
adaptation, evidence extraction) is logged with: input snapshot, output,
rationale, model/version, latency, cost. This is the single source for
"why did the system do this" — powering debugging, the parent-facing
evidence-chain transparency (ADR-009), and future fine-tuning/eval data.

## Consequences

- Repo layout gains `evaluation/` and `trace/` as top-level modules, peers
  of `agents/` and `world-model/`.
- No component may call an LLM outside the provider abstraction + trace
  wrapper.
