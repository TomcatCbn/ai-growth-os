"""Frontier Engine — code computes constraints, never the LLM (ADR-003).

A topic is on the frontier when all HARD prerequisites are mastered and the
topic itself is not yet mastered. Soft prerequisites are advisory and surface
in the candidate payload for the Planner's judgment.
"""

from __future__ import annotations

MASTERY_THRESHOLD = 0.7  # topic counts as "mastered" at/above this
AGE_OVERLAP = (4, 6)  # MVP band


def compute_frontier(
    topics: list[dict],
    dependencies: list[dict],
    topic_mastery: dict[str, dict],
    *,
    age: float,
    mastery_threshold: float = MASTERY_THRESHOLD,
) -> list[dict]:
    """Return frontier candidates with context for the Planner prompt.

    topics/dependencies follow the os-taxonomy schema (ADR-001).
    """
    hard_prereqs: dict[str, list[str]] = {}
    soft_prereqs: dict[str, list[str]] = {}
    for d in dependencies:
        bucket = hard_prereqs if d["strength"] == "hard" else soft_prereqs
        bucket.setdefault(d["topicId"], []).append(d["prerequisiteId"])

    def mastered(tid: str) -> bool:
        rec = topic_mastery.get(tid)
        if rec is None:
            return False  # untouched topics fall back to age prior: not mastered
        return rec.get("mastery", 0.0) >= mastery_threshold

    frontier = []
    for t in topics:
        if not (t["ageRangeStart"] <= age <= t["ageRangeEnd"]):
            continue
        if mastered(t["id"]):
            continue
        unmet_hard = [p for p in hard_prereqs.get(t["id"], []) if not mastered(p)]
        if unmet_hard:
            continue
        frontier.append(
            {
                "topic_id": t["id"],
                "name": t["name"],
                "subject": t["subject"],
                "domain": t["domain"],
                "evidence": t.get("evidence", []),
                "soft_prereq_gaps": [p for p in soft_prereqs.get(t["id"], []) if not mastered(p)],
                "centrality": t.get("centrality", 0.0),
            }
        )
    return frontier
