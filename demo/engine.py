"""ChildEngine — THE demo loop runtime for one virtual child.

Single implementation of the pipeline (guard → extract → events → reduce →
frontier → plan → arc → snapshot). The CLI (run_loop.py) and the web app
(web.py) both drive this — loop logic exists exactly once.

Offline via MockLLMProvider; live=True swaps in Claude. Pass logger=print
for CLI-style progress output.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo.arc import (
    CHECKIN_SIGNAL,
    generate_arc,
    load_patterns,
    load_targets,
    select_pattern,
)
from knowledge.i18n import I18n
from runtime.coach import ParentCoach
from runtime.events.store import EventStore
from runtime.evidence.extractor import EvidenceExtractor
from runtime.mission.manager import MissionManager
from runtime.planner.frontier import compute_frontier
from runtime.planner.planner import GrowthPlanner
from runtime.safety.guards import InputGuard, OutputGuard
from runtime.state.capabilities import (
    derive_capabilities,
    development_priorities,
    load_capability_map,
    topic_capabilities,
)
from runtime.state.memory import growth_memory_from_events
from runtime.state.reducer import reduce_events
from runtime.trace.trace import TrackedProvider
from runtime.twin import (
    next_callback,
    project_partner_state,
    project_tendencies,
    project_twin,
)

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = "knowledge/artifact/growth-artifact-0.1.json"
TAXONOMY = "world-model/capability-taxonomy.yaml"
CAPMAP = "world-model/topic-capability-map.yaml"


class ChildEngine:
    def __init__(
        self,
        profile_path: str,
        live: bool = False,
        db: str = ":memory:",
        artifact: str = ARTIFACT,
        taxonomy: str = TAXONOMY,
        capmap: str = CAPMAP,
        logger: Callable[[str], None] | None = None,
    ):
        self.profile = yaml.safe_load((ROOT / profile_path).read_text())
        self.artifact = json.loads((ROOT / artifact).read_text())
        self.taxonomy = yaml.safe_load((ROOT / taxonomy).read_text())

        child = self.profile["profile"]
        self.child = child
        self.child_id = child["child_id"]
        self.age = child["age"]
        self.state = dict(child["initial_state"])
        self.state.setdefault("interests", {})
        self.topics_by_id = {t["id"]: t for t in self.artifact["topics"]}

        self.store = EventStore(ROOT / db if db != ":memory:" else db)
        if live:
            from runtime.llm.claude import ClaudeProvider
            provider = ClaudeProvider()
        else:
            from demo.mock_llm import MockLLMProvider
            provider = MockLLMProvider()
        self.provider_name = provider.model
        llm = TrackedProvider(provider, self.store, component="child-engine")
        self.extractor = EvidenceExtractor(llm)
        self.planner = GrowthPlanner(llm)
        self.manager = MissionManager()
        self.in_guard, self.out_guard = InputGuard(), OutputGuard()
        self.targets = load_targets(self.artifact, self.taxonomy)
        self.cap_map = load_capability_map(ROOT / capmap, allow_mock=True)
        self.patterns = load_patterns()
        self.i18n = I18n()
        self.day = 0
        self.log: list[str] = []
        self._logger = logger

        # Restart recovery: replay growth + runtime state from the event log.
        prior = [vars(e) for e in self.store.events_for(self.child_id)]
        if prior:
            self.state.update(reduce_events(prior))
            self.manager = MissionManager.from_events(prior)
            self._emit(f"(recovered {len(prior)} events; active mission: "
                       f"{self.manager.active['arc_id'] if self.manager.active else 'none'})")

        for entry in self.profile.get("evidence_timeline", []):
            self.process(entry)

    def _emit(self, msg: str) -> None:
        self.log.append(msg)
        if self._logger:
            self._logger(msg)

    def derived_capabilities(self) -> dict:
        return derive_capabilities(
            self.state.get("topic_mastery", {}), self.state.get("capability_direct", {}),
            self.cap_map)

    # -- core loop ----------------------------------------------------------

    def process(self, entry: dict) -> None:
        self.day = max(self.day, entry.get("day", self.day + 1))
        day = entry.get("day", self.day)
        guarded = self.in_guard.screen(entry["raw_text"])
        self.store.append("evidence.submitted", self.child_id, {
            "day": day, "channel": entry["channel"], "raw_text": guarded.text,
            "guard_flags": guarded.flags,
        })
        signals = []

        if entry["channel"] == "mission_checkin" and self.manager.active:
            arc = self.manager.active
            signals.append({
                "target_type": "topic",
                "target_id": arc["primary_goal"]["topic_id"],
                "signal_strength": CHECKIN_SIGNAL[entry["checkin_status"]],
                "confidence": 0.7,
                "quote": guarded.text,
            })
            closed = self.manager.close(entry["checkin_status"])
            self.store.append("mission.closed", self.child_id, {
                "arc_id": closed["arc_id"], "verdict": closed["hypothesis_verdict"],
                "status": closed["status"]})
            self._emit(f"day {day}｜打卡「{entry['checkin_status']}」→ 冒险结束（假设{closed['hypothesis_verdict']}）")
        else:
            signals, _ = self.extractor.extract(
                child_id=self.child_id, raw_text=guarded.text, candidate_targets=self.targets)
            kinds = "、".join(self.i18n.capability_name(s["target_id"]) for s in signals) or "无信号"
            self._emit(f"day {day}｜{entry['channel']} → {kinds}")
            # Chapter progression: family activity days advance the arc.
            if self.manager.has_next_chapter():
                chapter = self.manager.advance_chapter()
                self.store.append("mission.chapter_advanced", self.child_id, {
                    "arc_id": self.manager.active["arc_id"],
                    "chapter_id": chapter["chapter_id"], "day": day})
                self._emit(f"day {day}｜↳ 进入第 {chapter['index']} 章「{chapter['title']}」")

        self.store.append("evidence.signals_extracted", self.child_id,
                          {"day": day, "signals": signals})

        events = [vars(e) for e in self.store.events_for(self.child_id)]
        self.state.update(reduce_events(events))

        if self.manager.active is None:
            self._plan_and_activate(events, day)

        self.store.save_snapshot(self.child_id, {
            "growth": self.state, "runtime": self.manager.snapshot()}, len(events))

    def _plan_and_activate(self, events: list[dict], day: int) -> None:
        frontier = compute_frontier(
            self.artifact["topics"], self.artifact["dependencies"],
            self.state.get("topic_mastery", {}), age=self.age)
        caps = self.derived_capabilities()
        for c in frontier:
            c["capability_targets"] = topic_capabilities(c["topic_id"], self.cap_map)
            c["development_priorities"] = development_priorities(
                self.cap_map, c["topic_id"], age=self.age)
        trigger = "cold_start" if not any(
            e["event_type"] == "mission.activated" for e in events
        ) else "evidence_submitted"
        plan, _ = self.planner.plan(
            child_id=self.child_id, child_state=self.state,
            frontier=frontier, recent_evidence=events[-10:], trigger=trigger,
            capabilities=caps, growth_memory=growth_memory_from_events(events))
        topic = self.topics_by_id[plan["selected_topic_id"]]
        theme = max(self.state["interests"], key=self.state["interests"].get).split(".")[-1]
        pattern = select_pattern(self.patterns, topic_capabilities(topic["id"], self.cap_map), events)
        partner_state = project_partner_state(self.child_id, events)
        callback = next_callback(partner_state)
        arc = generate_arc(topic, theme, self.child_id, self.child["name"],
                           self.i18n, pattern, callback=callback)
        if not self.i18n.has_topic_zh(topic["id"]):
            self._emit(f"day {day}｜⚠ i18n 缺口：{topic['name']} 的观察清单回退为英文")
        check = self.out_guard.review_arc(arc)
        rationale_check = self.out_guard.review(plan["rationale"], audience="parent")
        if not (check.passed and rationale_check.passed):
            flags = check.flags + rationale_check.flags
            self.store.append_safety("safety.output_rejected", self.child_id, {"flags": flags})
            self._emit(f"day {day}｜⚠ 安全护栏拦截了任务生成：{flags}")
            return
        self.manager.activate(arc)
        self.store.append("mission.activated", self.child_id, {
            "arc_id": arc["arc_id"], "topic": topic["id"], "theme": theme,
            "pattern_id": pattern["pattern_id"],
            "plan_trace": plan["decision_trace_id"],
            "arc": arc, "activated_at": self.manager.activated_at})
        if callback:
            self.store.append("partner.callback_used", self.child_id, {
                "moment": callback["moment"],
                "source_event_id": callback["source_event_id"],
                "arc_id": arc["arc_id"]})
        tname = self.i18n.topic_name(topic["id"], topic["name"])
        self._emit(f"day {day}｜▶ 新冒险「{theme}·{tname}」模式={pattern['name_zh']}（候选池 {len(frontier)}）")

    def submit(self, channel: str, raw_text: str, checkin_status: str | None = None) -> None:
        entry = {"day": self.day + 1, "channel": channel, "raw_text": raw_text}
        if channel == "mission_checkin":
            entry["checkin_status"] = checkin_status or "completed"
        self.process(entry)

    # -- view ----------------------------------------------------------------

    def view(self) -> dict:
        derived = self.derived_capabilities()
        caps = [
            {"name": self.i18n.capability_name(cid), "level": r["score"],
             "conf": r["confidence"],
             "n": r["topic_evidence_count"] + r["direct_evidence_count"]}
            for cid, r in sorted(derived.items(), key=lambda kv: -kv[1]["score"])
        ]
        topics = [
            {"name": self.i18n.topic_name(tid, self.topics_by_id.get(tid, {}).get("name", tid)),
             "mastery": r["mastery"], "n": r["evidence_count"]}
            for tid, r in sorted(self.state.get("topic_mastery", {}).items(),
                                 key=lambda kv: -kv[1]["mastery"])
        ]
        interests = sorted(self.state["interests"].items(), key=lambda kv: -kv[1])[:6]
        coach = ParentCoach(self.taxonomy, self.i18n, self.out_guard, topic_names={
            tid: self.i18n.topic_name(tid, t["name"])
            for tid, t in self.topics_by_id.items()})
        events = [vars(e) for e in self.store.events_for(self.child_id)]
        insight = coach.build_insight(
            child_id=self.child_id, events=events, capabilities=derived)
        twin = project_twin(
            child=self.child, events=events, state=self.state, capabilities=derived)
        tendencies = project_tendencies(events)
        partner = project_partner_state(self.child_id, events)
        arc = self.manager.active
        if arc:
            topic = self.topics_by_id.get(arc["primary_goal"]["topic_id"], {})
            arc = dict(arc)
            arc["goal_name"] = self.i18n.topic_name(topic.get("id", ""), topic.get("name", ""))
            # i18n fallback must be visible on the parent surface, never silent.
            arc["i18n_gap"] = not self.i18n.has_topic_zh(topic.get("id", ""))
        return {
            "child": self.child, "provider": self.provider_name,
            "caps": caps, "topics": topics, "interests": interests,
            "arc": arc, "log": self.log[-15:][::-1],
            "insight": insight,
            "twin": twin, "tendencies": tendencies, "partner": partner,
            "n_events": len(self.store.events_for(self.child_id)),
        }
