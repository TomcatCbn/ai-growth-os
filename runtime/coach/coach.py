"""Parent Coach — minimal weekly ParentInsight (ADR-009).

Deterministic v1 (no LLM): moments from the strongest evidence quotes,
trends from first-half vs second-half signal movement, one suggestion from
the highest-priority weakest capability. Iron rules enforced in code:
never compare (only the child's own past), every trend carries its evidence
chain, suggestions are low-cost home activities. No scores, no rankings,
no diagnosis in the output text.

Closed loop: Evidence → Growth Insight → Parent Coach → Family Action →
More Evidence.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from ..contracts import validate
from ..safety.guards import OutputGuard

# Comparison/diagnosis phrasing is banned in parent-facing insight text.
_BANNED_PATTERNS = ["比其他孩子", "同龄", "落后", "超前", "诊断", "排名"]

_ACTIVITY = {
    "cognitive": "晚饭时玩「找规律」：用筷子和勺子摆一串规律，请孩子接着摆。",
    "language": "睡前请孩子把今天的一件事讲成有开头、有结尾的小故事。",
    "social_emotional": "玩轮流游戏：一人搭一块积木，中途故意停顿，等孩子提醒。",
    "creativity": "用纸箱和玩偶搭一个「商店」，请孩子当店主编一段叫卖词。",
    "executive_function": "出门前请孩子自己列三样要带的东西，说完再检查。",
    "physical": "夹豆子比赛：用筷子把豆子从一个碗夹到另一个碗，计时一分钟。",
}


class ParentCoach:
    def __init__(self, taxonomy: dict, i18n, out_guard: OutputGuard | None = None,
                 topic_names: dict[str, str] | None = None):
        self._taxonomy = taxonomy
        self._i18n = i18n
        self._guard = out_guard or OutputGuard()
        self._topic_names = topic_names or {}
        self._domain_by_cap = {
            c["id"]: domain
            for domain, d in taxonomy["domains"].items()
            for c in d["capabilities"]
        }
        self._priority_by_cap = {
            c["id"]: c.get("priority", {})
            for d in taxonomy["domains"].values()
            for c in d["capabilities"]
        }

    def build_insight(
        self,
        *,
        child_id: str,
        events: list[dict],
        capabilities: dict[str, dict],
        period: tuple[str, str] | None = None,
    ) -> dict:
        """Build a ParentInsight from the event stream + derived capability
        view. Validates against the contract and passes the Output Guard
        before returning — unreviewed text never reaches parents."""
        signal_events = [
            e for e in events if e.get("event_type") == "evidence.signals_extracted"
        ]
        moments = self._moments(signal_events)
        trends = self._trends(signal_events)
        suggestion = self._suggestion(capabilities)
        now = datetime.now(UTC).isoformat()
        insight = {
            "insight_id": f"ins_{uuid.uuid4().hex[:10]}",
            "child_id": child_id,
            "period": {
                "start": period[0] if period else (
                    signal_events[0]["created_at"] if signal_events else now),
                "end": period[1] if period else now,
            },
            "moments": moments or [{
                "title": "本周还没有足够的观察记录",
                "evidence_quotes": ["（暂无）"],
            }],
            "trends": trends,
            "suggestion": suggestion,
            "created_at": now,
        }
        validate("parent-insight", insight)
        self._check_language(insight)
        return insight

    # -- parts ----------------------------------------------------------------

    def _moments(self, signal_events: list[dict]) -> list[dict]:
        """Strongest signal per target, with its verbatim quote — the trust
        currency (ADR-009)."""
        best: dict[str, tuple[float, str, str]] = {}
        for e in signal_events:
            day = e["payload"].get("day", "?")
            for s in e["payload"].get("signals", []):
                key = s["target_id"]
                score = s["signal_strength"] * s["confidence"]
                if key not in best or score > best[key][0]:
                    best[key] = (score, s["quote"], f"第{day}天")
        moments = []
        for target, (_, quote, when) in sorted(best.items(), key=lambda kv: -kv[1][0])[:3]:
            if target.startswith("capability."):
                name = self._i18n.capability_name(target)
            else:
                name = self._topic_names.get(target, target)
            moments.append({
                "title": f"{when}，孩子在「{name}」上露出了新苗头",
                "evidence_quotes": [quote],
                "related_capabilities": [target] if target.startswith("capability.") else [],
            })
        return moments

    def _trends(self, signal_events: list[dict]) -> list[dict]:
        """Direction per capability, vs. the child's own past only."""
        per_cap: dict[str, list[tuple[float, str]]] = {}
        for e in signal_events:
            for s in e["payload"].get("signals", []):
                if s["target_type"] != "capability":
                    continue
                per_cap.setdefault(s["target_id"], []).append(
                    (s["signal_strength"], e["event_id"]))
        trends = []
        for cap, entries in sorted(per_cap.items()):
            strengths = [x[0] for x in entries]
            if len(strengths) >= 2:
                half = max(1, len(strengths) // 2)
                diff = (sum(strengths[-half:]) / half) - (sum(strengths[:half]) / half)
                direction = "up" if diff > 0.1 else "down" if diff < -0.1 else "steady"
            else:
                direction = "steady"
            name = self._i18n.capability_name(cap)
            reading = {"up": "最近的信号比之前更强", "steady": "表现平稳",
                       "down": "最近出现得少了，值得留意"}[direction]
            trends.append({
                "capability_id": cap,
                "direction": direction,
                "interpretation": f"「{name}」{reading}（只和孩子自己前段比）。",
                "evidence_refs": [eid for _, eid in entries],
            })
        return trends

    def _suggestion(self, capabilities: dict[str, dict]) -> dict:
        """One low-cost activity for the highest-priority weakest capability.
        Unobserved capabilities get a neutral prior (0.5), so a capability the
        child actually struggled with outranks a never-observed one."""
        best_cap, best_priority = None, -1.0
        for cap, prios in self._priority_by_cap.items():
            prio = max(prios.values()) if prios else 0.0
            score = capabilities.get(cap, {}).get("score", 0.5)
            priority = prio * (1.0 - score)
            if priority > best_priority:
                best_cap, best_priority = cap, priority
        name = self._i18n.capability_name(best_cap) if best_cap else "探索"
        domain = self._domain_by_cap.get(best_cap, "cognitive")
        return {
            "title": f"本周小练习：{name}",
            "home_activity": _ACTIVITY.get(domain, _ACTIVITY["cognitive"]),
        }

    def _check_language(self, insight: dict) -> None:
        """Iron rules (ADR-009): no comparison, no diagnosis — and everything
        passes the Output Guard before reaching parent eyes."""
        texts: list[str] = []
        for m in insight["moments"]:
            texts.append(m["title"])
        for t in insight["trends"]:
            texts.append(t["interpretation"])
        texts += [insight["suggestion"]["title"], insight["suggestion"]["home_activity"]]
        for text in texts:
            for banned in _BANNED_PATTERNS:
                if banned in text:
                    raise ValueError(f"insight text violates iron rule: {banned!r} in {text!r}")
        result = self._guard.review(" ".join(texts), audience="parent")
        if not result.passed:
            raise ValueError(f"output guard rejected insight: {result.flags}")
