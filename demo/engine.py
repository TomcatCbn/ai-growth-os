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
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo.arc import (
    CHECKIN_SIGNAL,
    generate_arc,
    load_adventure_templates,
    load_patterns,
    load_targets,
    pace_adjustment,
    select_pattern,
    select_template,
)
from knowledge.i18n import I18n
from runtime.coach import ParentCoach
from runtime.contracts import ContractViolation, validate
from runtime.events.store import EventStore
from runtime.evidence.extractor import EvidenceExtractor
from runtime.metrics import relationship_metrics
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
from runtime.story import emit_session
from runtime.trace.trace import TrackedProvider
from runtime.twin import (
    next_callback,
    project_partner_state,
    project_tendencies,
    project_twin,
)
from runtime.twin.family import build_family_account, build_family_model

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
        self.targets = load_targets(self.artifact, self.taxonomy)
        # Mock maps are for offline demo/baseline only; a live run must use
        # an adjudicated map — checked BEFORE any provider is constructed
        # (gate: UnadjudicatedAssetError otherwise).
        self.cap_map = load_capability_map(ROOT / capmap, allow_mock=not live)
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
        self.patterns = load_patterns()
        self.adventure_templates = load_adventure_templates()
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

        # The event log is the system of record (ADR-016): profile timeline
        # entries already in the log must NOT be re-injected. Keyed by
        # (day, channel, raw_text) — a second, DIFFERENT observation on the
        # same day is new evidence and must be processed.
        processed = {
            (e.payload.get("day"), e.payload.get("channel"),
             e.payload.get("raw_text"))
            for e in self.store.events_for(self.child_id)
            if e.event_type == "evidence.submitted"
        }
        for entry in self.profile.get("evidence_timeline", []):
            key = (entry.get("day"), entry["channel"],
                   self.in_guard.screen(entry["raw_text"]).text)
            if key in processed:
                continue
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
        # Full Evidence contract validation before the fact is recorded
        # (ADR-002): every evidence.submitted is a complete Evidence object.
        evidence_id = f"ev_{uuid.uuid4().hex[:12]}"
        evidence = {
            "evidence_id": evidence_id,
            "child_id": self.child_id,
            "channel": entry["channel"],
            "submitted_by": entry.get("submitted_by", "parent"),
            "raw_text": guarded.text,
            "created_at": datetime.now(UTC).isoformat(),
            "day": day,
            "guard_flags": guarded.flags,
        }
        if entry["channel"] == "mission_checkin":
            evidence["checkin_status"] = entry.get("checkin_status", "completed")
        validate("evidence", evidence)
        self.store.append("evidence.submitted", self.child_id, evidence,
                          event_id=evidence_id)
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
        family = build_family_model(
            self.child_id, self.profile.get("family"), self.state["interests"])
        plan, _ = self.planner.plan(
            child_id=self.child_id, child_state=self.state,
            frontier=frontier, recent_evidence=events[-10:], trigger=trigger,
            capabilities=caps, growth_memory=growth_memory_from_events(events),
            family_goals=family["goals"])
        topic = self.topics_by_id[plan["selected_topic_id"]]
        theme = max(self.state["interests"], key=self.state["interests"].get).split(".")[-1]
        pattern = select_pattern(
            self.patterns, topic_capabilities(topic["id"], self.cap_map),
            events, pace=pace_adjustment(events))
        template = select_template(self.adventure_templates, pattern["pattern_id"], events)
        partner_state = project_partner_state(self.child_id, events)
        callback = next_callback(partner_state)
        arc = generate_arc(topic, theme, self.child_id, self.child["name"],
                           self.i18n, pattern, callback=callback, template=template)
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
            "template_id": template["template_id"] if template else None,
            "plan_trace": plan["decision_trace_id"],
            "arc": arc, "activated_at": self.manager.activated_at, "day": day})
        tname = self.i18n.topic_name(topic["id"], topic["name"])
        tname_tpl = f"·{template['name_zh']}" if template else ""
        self._emit(f"day {day}｜▶ 新冒险「{theme}·{tname}{tname_tpl}」模式={pattern['name_zh']}（候选池 {len(frontier)}）")

    def submit(self, channel: str, raw_text: str, checkin_status: str | None = None) -> None:
        entry = {"day": self.day + 1, "channel": channel, "raw_text": raw_text}
        if channel == "mission_checkin":
            entry["checkin_status"] = checkin_status or "completed"
        self.process(entry)

    # -- sessions (Phase 0 vertical loop) -------------------------------------

    def start_session(self, launch_source: str = "child_mode") -> dict:
        """Child opens the app → Runtime JSON session for the active chapter.
        The FULL session document is stored in the event payload, so player
        state rebuilds from the event log after any restart (ADR-016).
        launch_source is an honest entry label: child_mode (the player's own
        start button) vs parent_preview (from the parent dashboard)."""
        if launch_source not in ("child_mode", "parent_preview"):
            raise ValueError(f"unknown launch_source: {launch_source}")
        arc = self.manager.active
        if arc is None:
            raise RuntimeError("no active mission — plan one first")
        chapter = next(c for c in arc["chapters"] if c["status"] == "active")
        session = emit_session(arc, chapter)
        callback = self._session_callback_moment(session)
        if callback:
            session["callback_moment"] = callback
        self.store.append("session.started", self.child_id, {
            "session_id": session["session_id"], "arc_id": arc["arc_id"],
            "chapter_id": chapter["chapter_id"],
            "date": datetime.now(UTC).date().isoformat(),
            "launch_source": launch_source,
            "session": session,
        })
        return session

    def _session_callback_moment(self, session: dict) -> str | None:
        for seg in session["segments"]:
            for n in seg["scene"]["nodes"]:
                if n["type"] == "dialogue" and "还记得我们的" in n.get("text", ""):
                    text = n["text"]
                    return text.split("还记得我们的", 1)[1].split("吗？", 1)[0]
        return None

    def get_session(self, session_id: str) -> dict | None:
        """Rebuild a session document from the event log (restart-safe)."""
        for e in self.store.events_for(self.child_id):
            if (e.event_type == "session.started"
                    and e.payload.get("session_id") == session_id):
                return e.payload.get("session")
        return None

    def record_interaction(self, session_id: str, node_type: str, data: dict) -> None:
        """A real child interaction (choice made, voice answer, callback
        response). Contract-validated: the session must exist, the node type
        must match a node in its Scene DSL, and choices must be legal."""
        interaction = {"session_id": session_id, "node_type": node_type, **data}
        validate("session-interaction", interaction)

        session = self.get_session(session_id)
        if session is None:
            raise ContractViolation(f"unknown session: {session_id}")
        nodes = [
            n for seg in session["segments"] for n in seg["scene"]["nodes"]
        ]
        if node_type in ("choice", "voice"):
            typed = [n for n in nodes if n["type"] == node_type]
            if not typed:
                raise ContractViolation(
                    f"session {session_id} has no {node_type} node")
            if node_type == "choice":
                legal = {o["id"] for n in typed for o in n.get("options", [])}
                if data.get("choice_id") not in legal:
                    raise ContractViolation(
                        f"illegal choice_id {data.get('choice_id')}; legal: {legal}")
        elif node_type in ("callback_shown", "callback_recognized"):
            if data.get("moment") != session.get("callback_moment"):
                raise ContractViolation(
                    f"callback moment mismatch for session {session_id}")

        self.store.append("session.interaction", self.child_id, {
            "session_id": session_id, "node_type": node_type,
            "date": datetime.now(UTC).date().isoformat(), **data,
        })
        # Callback events are produced ONLY by real player interactions —
        # offered when the child actually sees it, recognized/ignored by
        # the child's own answer.
        if node_type == "callback_shown":
            self.store.append("partner.callback_offered", self.child_id, {
                "moment": data["moment"], "session_id": session_id})
        elif node_type == "callback_recognized":
            self.store.append("partner.callback_recognized", self.child_id, {
                "moment": data["moment"], "response": data["response"],
                "session_id": session_id})

    def request_doudou(self) -> None:
        """The child spontaneously asked for Doudou — the strongest
        relationship signal we can record."""
        self.store.append("child.requested_doudou", self.child_id,
                          {"date": datetime.now(UTC).date().isoformat()})

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
        family = build_family_model(
            self.child_id, self.profile.get("family"), self.state["interests"])
        family_account = build_family_account(self.child, self.profile.get("family"))
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
            "family": family, "family_account": family_account,
            "metrics": relationship_metrics(events),
            "n_events": len(self.store.events_for(self.child_id)),
        }
