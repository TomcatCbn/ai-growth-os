"""Demo loop — drives a virtual child through the 2-week core loop (Q18/19).

Pipeline per timeline entry (all ADR constraints enforced):
  raw text → InputGuard → evidence event → extraction (LLM/mock)
  → signals event → Reducer (state) → [mission close on check-in]
  → frontier (code) → plan (LLM within frontier) → arc → MissionManager
  → snapshot.

Offline by default (MockLLMProvider). With ANTHROPIC_API_KEY + --live it
runs the identical loop through Claude.

Usage:
  python demo/run_loop.py --profile demo/virtual_children/curious_low_persistence.yaml \
      --artifact knowledge/artifact/growth-artifact-0.1.json [--live]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.events.store import EventStore  # noqa: E402
from runtime.evidence.extractor import EvidenceExtractor  # noqa: E402
from runtime.mission.manager import MissionManager  # noqa: E402
from runtime.planner.frontier import compute_frontier  # noqa: E402
from runtime.planner.planner import GrowthPlanner  # noqa: E402
from runtime.safety.guards import InputGuard, OutputGuard  # noqa: E402
from runtime.state.reducer import reduce_events  # noqa: E402
from runtime.trace.trace import TrackedProvider  # noqa: E402
from knowledge.i18n import I18n  # noqa: E402

CHECKIN_SIGNAL = {"completed": 0.8, "partial": 0.5, "not_completed": 0.2}

# Observation-point phrasing is intentionally English here (canonical
# knowledge stays English, ADR-005); zh polish arrives with the i18n layer.
ARC_TEMPLATES = [
    ("发现密码", "豆豆兔在{theme}森林深处发现了一扇锁住的门，门上刻着奇怪的图案。",
     "和孩子一起在家里找 3 个有规律的图案（窗帘、地砖、瓷砖），说说规律是什么。",
     "让豆豆兔听听：你们找到了什么图案？它是怎么重复的？"),
    ("破解障碍", "门上的图案原来是一串密码！豆豆兔需要你帮忙找出下一个图案。",
     "用积木/彩珠摆一串 ABAB 规律，让孩子接着摆 3 个；再试试 ABB 规律。",
     "孩子摆的规律是什么？请他教教豆豆兔。"),
    ("打开大门", "最后一道密码最难——这次要孩子自己设计一串密码保护宝藏！",
     "请孩子自己创造一串规律（动作、声音或物品都行），家长来猜规律。",
     "孩子设计的密码是什么？豆豆兔猜对了吗？"),
]


def load_targets(artifact: dict, taxonomy: dict) -> list[dict]:
    targets = [{"id": t["id"], "name": t["name"]} for t in artifact["topics"]]
    for domain in taxonomy["domains"].values():
        for cap in domain["capabilities"]:
            targets.append({"id": cap["id"], "name": cap["name_zh"]})
    return targets


def generate_arc(topic: dict, theme: str, child_name: str, i18n: I18n) -> dict:
    # Observation checklist: human-polished zh where available (ADR-005 §4),
    # canonical English otherwise.
    checklist = i18n.topic_evidence_zh(topic["id"], topic.get("evidence", []))[:3]
    topic_name = i18n.topic_name(topic["id"], topic["name"])
    chapters = []
    for i, (title, narration, task, ret) in enumerate(ARC_TEMPLATES, start=1):
        chapters.append(
            {
                "chapter_id": f"ch_{i}",
                "index": i,
                "title": title,
                "narration": narration.format(theme=theme),
                "real_world_task": task,
                "return_prompt": ret,
                "observation_checklist": checklist,
                "difficulty": i,
                "interaction_mode": "parent_card",
                "default_modality": "voice_story",
                "status": "pending",
            }
        )
    return {
        "child_name": child_name,
        "status": "draft",
        "primary_goal": {"topic_id": topic["id"], "capability_ids": []},
        "supporting_goals": [],
        "growth_hypothesis": {
            "statement": f"通过{theme}主题冒险，孩子将在「{topic_name}」上展现可见进步。",
            "expected_mastery_delta": 0.2,
            "key_signal": checklist[0] if checklist else "观察孩子是否主动迁移到新情境",
        },
        "interest_theme": theme,
        "chapters": chapters,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--taxonomy", default="world-model/capability-taxonomy.yaml")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--db", default=":memory:")
    args = ap.parse_args()

    profile = yaml.safe_load(Path(args.profile).read_text())
    artifact = json.loads(Path(args.artifact).read_text())
    taxonomy = yaml.safe_load(Path(args.taxonomy).read_text())

    child = profile["profile"]
    child_id, age = child["child_id"], child["age"]
    state = child["initial_state"]
    topics_by_id = {t["id"]: t for t in artifact["topics"]}

    store = EventStore(args.db)
    if args.live:
        from runtime.llm.claude import ClaudeProvider
        provider = ClaudeProvider()
    else:
        from demo.mock_llm import MockLLMProvider
        provider = MockLLMProvider()
    llm = TrackedProvider(provider, store, component="demo-loop")
    extractor = EvidenceExtractor(llm)
    planner = GrowthPlanner(llm)
    manager = MissionManager()
    in_guard, out_guard = InputGuard(), OutputGuard()
    targets = load_targets(artifact, taxonomy)
    i18n = I18n()

    print(f"=== {child['name']} ({child_id}, age {age}) | provider={provider.model} ===\n")

    for entry in profile["evidence_timeline"]:
        day = entry["day"]
        guarded = in_guard.screen(entry["raw_text"])
        store.append("evidence.submitted", child_id, {
            "day": day, "channel": entry["channel"], "raw_text": guarded.text,
            "guard_flags": guarded.flags,
        })
        signals = []

        if entry["channel"] == "mission_checkin" and manager.active:
            arc = manager.active
            signals.append({
                "target_type": "topic",
                "target_id": arc["primary_goal"]["topic_id"],
                "signal_strength": CHECKIN_SIGNAL[entry["checkin_status"]],
                "confidence": 0.7,
                "quote": guarded.text,
            })
            closed = manager.close(entry["checkin_status"])
            store.append("mission.closed", child_id, {
                "arc_id": closed["arc_id"], "verdict": closed["hypothesis_verdict"]})
            print(f"day {day:>2} | check-in {entry['checkin_status']:<13} → mission closed "
                  f"(verdict: {closed['hypothesis_verdict']})")
        else:
            signals, _ = extractor.extract(
                child_id=child_id, raw_text=guarded.text, candidate_targets=targets)
            kinds = ", ".join(s["target_id"].split(".")[-1] for s in signals) or "—"
            print(f"day {day:>2} | {entry['channel']:<17} → signals: {kinds}")

        store.append("evidence.signals_extracted", child_id, {"day": day, "signals": signals})

        # Reduce (full replay — cheap at demo scale)
        events = [vars(e) for e in store.events_for(child_id)]
        reduced = reduce_events(events)
        state.update(reduced)

        # Re-plan trigger: no active mission → plan + generate arc (ADR-006)
        if manager.active is None:
            frontier = compute_frontier(
                artifact["topics"], artifact["dependencies"],
                state.get("topic_mastery", {}), age=age)
            plan, _ = planner.plan(
                child_id=child_id, child_state=state,
                frontier=frontier, recent_evidence=events[-10:])
            topic = topics_by_id[plan["selected_topic_id"]]
            theme = max(state.get("interests", {"冒险": 1}), key=state.get("interests", {}).get)
            theme = theme.split(".")[-1]
            arc = generate_arc(topic, theme, child["name"], i18n)
            content_check = out_guard.review(
                " ".join(c["narration"] for c in arc["chapters"]), audience="child")
            if not content_check.passed:
                store.append("safety.output_rejected", child_id, {"flags": content_check.flags})
                print(f"         ⚠ output guard rejected arc: {content_check.flags}")
                continue
            manager.activate(arc)
            store.append("mission.activated", child_id, {
                "arc_id": arc["arc_id"], "topic": topic["id"], "theme": theme,
                "plan_trace": plan["decision_trace_id"]})
            print(f"         ▶ new arc 「{arc['chapters'][0]['title']}」theme={theme} "
                  f"goal={topic['name']} (frontier={len(frontier)})")

        store.save_snapshot(child_id, state, len(events))

    print("\n--- final state ---")
    tm = state.get("topic_mastery", {})
    for tid, rec in sorted(tm.items(), key=lambda kv: -kv[1]["mastery"])[:5]:
        name = topics_by_id.get(tid, {}).get("name", tid)
        print(f"  topic  {name[:45]:<47} mastery={rec['mastery']:.2f} n={rec['evidence_count']}")
    for cid, rec in sorted(state.get("capability_direct", {}).items(),
                           key=lambda kv: -kv[1]["level"])[:6]:
        print(f"  cap    {cid.split('.')[-1]:<25} level={rec['level']:.2f} "
              f"conf={rec['confidence']:.2f} n={rec['evidence_count']}")
    print(f"  events={len(store.events_for(child_id))}")


if __name__ == "__main__":
    main()
