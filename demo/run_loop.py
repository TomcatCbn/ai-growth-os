"""Demo CLI — thin shell over ChildEngine (the single loop implementation).

Usage:
  python demo/run_loop.py --profile demo/virtual_children/curious_low_persistence.yaml \
      --artifact knowledge/artifact/growth-artifact-0.1.json [--live] [--db path]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo.engine import ARTIFACT, CAPMAP, TAXONOMY, ChildEngine


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--artifact", default=ARTIFACT)
    ap.add_argument("--taxonomy", default=TAXONOMY)
    ap.add_argument("--capmap", default=CAPMAP)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--db", default=":memory:")
    args = ap.parse_args()

    engine = ChildEngine(
        args.profile, live=args.live, db=args.db, artifact=args.artifact,
        taxonomy=args.taxonomy, capmap=args.capmap)
    child = engine.child
    print(f"=== {child['name']} ({engine.child_id}, age {engine.age}) "
          f"| provider={engine.provider_name} ===\n")
    for line in engine.log:
        print(line)

    print("\n--- final state ---")
    tm = engine.state.get("topic_mastery", {})
    for tid, rec in sorted(tm.items(), key=lambda kv: -kv[1]["mastery"])[:5]:
        name = engine.topics_by_id.get(tid, {}).get("name", tid)
        print(f"  topic  {name[:45]:<47} mastery={rec['mastery']:.2f} n={rec['evidence_count']}")
    caps = engine.derived_capabilities()
    for cid, rec in sorted(caps.items(), key=lambda kv: -kv[1]["score"])[:6]:
        print(f"  cap    {cid.split('.')[-1]:<25} score={rec['score']:.2f} "
              f"(topic={rec['topic_derived']}, direct={rec['direct']}) "
              f"conf={rec['confidence']:.2f}")
    print(f"  events={len(engine.store.events_for(engine.child_id))}")

    # Close the family loop: Evidence → Insight → Parent Coach → Family Action.
    view = engine.view()
    engine.store.append("parent.insight_generated", engine.child_id,
                        {"insight": view["insight"]})
    insight = view["insight"]
    print("\n--- parent insight ---")
    for m in insight["moments"]:
        print(f"  ✦ {m['title']}")
    for t in insight["trends"][:4]:
        name = engine.i18n.capability_name(t["capability_id"])
        print(f"  {t['direction']:<6} {name}: {t['interpretation']}")
    print(f"  建议  {insight['suggestion']['title']}：{insight['suggestion']['home_activity']}")


if __name__ == "__main__":
    main()
