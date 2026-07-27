# Product Experience Before Trial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Phase 0 web demo into a touch-safe, voice-enabled, multi-day child experience that passes an internal readiness gate before a 7–14 day real-child trial.

**Architecture:** Keep the FastAPI modular monolith and Scene DSL contracts. Extract the browser player into focused static CSS/JS modules, keep source identity server-issued, add bounded versioned assets and voice metadata, and derive the experiment dashboard from the existing event log without adding a second source of truth.

**Tech Stack:** Python 3.12+, FastAPI, Jinja2, vanilla JavaScript/CSS, JSON Schema, SQLite event store, pytest, Playwright.

**Design:** `docs/superpowers/specs/2026-07-27-product-experience-before-trial-design.md`

---

## Delivery table

| Priority | Work package | Estimate | Depends on | Main output | Exit criterion |
|---|---|---:|---|---|---|
| P0 | Canonical run contract | 0.5 day | — | All local commands use port 8767 | Smoke test returns 200 for `/`, `/player`, and one asset |
| P1 | Player state machine and touch safety | 2 days | P0 | Retryable, duplicate-safe child journey | Browser failure/retry and full-journey tests pass |
| P2 | Responsive forest and Doudou motion | 2 days | P1 | Phone/tablet stage with bounded visual states | 390×844 and 768×1024 checks pass |
| P3 | Fixed voice and deterministic pacing | 2.5 days | P1 | `doudou_v1`, cached clips, complete text fallback | Audio-enabled and audio-blocked journeys pass |
| P4 | Trial content and continuity | 2 days | P1, P3 | Minimum coherent multi-day callback sequence | Callback matrix contains no missing next-day link |
| P5 | Experiment identity and readiness view | 2 days | P1, P4 | Stable participant route and data-health cards | Preview isolation and projection tests pass |
| P6 | Internal acceptance gate | 1 day | P2–P5 | Automated gate plus manual device checklist | One command produces PASS and checklist is signed |
| P7 | Real-child experiment | 7–14 calendar days | P6 | Relationship evidence and review record | Phase 0 metrics reviewed against declared thresholds |

**Implementation effort before trial:** approximately 12 engineering days, excluding the 7–14 calendar-day experiment.

## File map

| Path | Responsibility |
|---|---|
| `demo/templates/player.html` | Minimal semantic player shell and server-injected configuration |
| `demo/static/player.css` | Responsive forest stage, controls, motion, reduced-motion rules |
| `demo/static/player.js` | Player state machine, API client, retry and pacing behavior |
| `demo/static/asset-manifest.json` | Reviewed semantic visual and audio asset mapping |
| `demo/web.py` | Entry issuance, session endpoints, static mounting, readiness route |
| `runtime/story/emitter.py` | Scene DSL voice and pacing metadata emission |
| `runtime/voice/catalog.py` | Fixed voice identity and deterministic clip lookup |
| `runtime/metrics/readiness.py` | Read-only experiment data-health projection |
| `world-model/trial-content.yaml` | Bounded multi-day trial continuity matrix |
| `scripts/browser_walk.py` | Happy-path browser regression on port 8767 |
| `scripts/browser_resilience.py` | Network failure, audio fallback, duplicate-tap regression |
| `scripts/trial_readiness.py` | One-command automated readiness gate |
| `tests/test_player_contract.py` | Template/static contract and asset manifest tests |
| `tests/test_voice.py` | Voice catalog and emitter behavior |
| `tests/test_trial_content.py` | Multi-day content and callback linkage |
| `tests/test_readiness.py` | Data-health and preview-isolation projection |
| `docs/trial/acceptance-checklist.md` | Manual phone/tablet internal acceptance |
| `docs/trial/protocol.md` | Participant setup, daily procedure, stop conditions, review |

---

### Task 1: Canonicalize the 8767 run contract

**Files:**
- Modify: `demo/web.py`
- Modify: `README.md`
- Modify: `docs/next-steps.md`
- Test: `tests/test_player_contract.py`

- [ ] **Step 1: Write the failing documentation contract test**

```python
from pathlib import Path


def test_demo_commands_use_canonical_port_8767():
    root = Path(__file__).resolve().parent.parent
    sources = [root / "README.md", root / "demo/web.py", root / "scripts/browser_walk.py"]
    text = "\n".join(path.read_text() for path in sources)
    assert "8765" not in text
    assert "--port 8767" in text
```

- [ ] **Step 2: Run the test and confirm the stale command fails**

Run: `.venv/bin/python -m pytest tests/test_player_contract.py -q`

Expected: FAIL because `demo/web.py` still documents port 8765.

- [ ] **Step 3: Update the run commands**

Use this canonical command everywhere:

```bash
.venv/bin/python -m uvicorn demo.web:app --host 127.0.0.1 --port 8767
```

Add these routes to the README smoke instructions:

```text
Dashboard: http://127.0.0.1:8767/
Child:     http://127.0.0.1:8767/player?child=vc_curious
Preview:   http://127.0.0.1:8767/preview?child=vc_curious
```

- [ ] **Step 4: Verify tests and smoke endpoints**

Run: `.venv/bin/python -m pytest tests/test_player_contract.py -q`

Expected: PASS.

Run while the server is active:

```bash
curl -fsS http://127.0.0.1:8767/ >/dev/null
curl -fsS 'http://127.0.0.1:8767/player?child=vc_curious' >/dev/null
curl -fsS http://127.0.0.1:8767/assets/character/doudou/emotion/happy.svg >/dev/null
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/next-steps.md demo/web.py tests/test_player_contract.py
git commit -m "docs: standardize demo on port 8767"
```

---

### Task 2: Extract a testable player shell

**Files:**
- Create: `demo/static/player.css`
- Create: `demo/static/player.js`
- Modify: `demo/templates/player.html`
- Modify: `demo/web.py`
- Test: `tests/test_player_contract.py`

- [ ] **Step 1: Add a failing shell contract test**

```python
from fastapi.testclient import TestClient
from demo.web import app


def test_player_uses_versioned_static_modules():
    with TestClient(app) as client:
        page = client.get("/player", params={"child": "vc_curious"})
    assert page.status_code == 200
    assert '<link rel="stylesheet" href="/static/player.css">' in page.text
    assert '<script type="module" src="/static/player.js"></script>' in page.text
    assert "function showNode()" not in page.text
```

- [ ] **Step 2: Run the test and verify failure**

Run: `.venv/bin/python -m pytest tests/test_player_contract.py::test_player_uses_versioned_static_modules -q`

Expected: FAIL because CSS and JavaScript are inline.

- [ ] **Step 3: Mount the static directory and reduce the template to configuration**

Add to `demo/web.py`:

```python
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)
```

The template must expose only this page-local configuration:

```html
<div id="player-app"
     data-child-id="{{ child_id }}"
     data-entry-id="{{ entry_id }}"
     data-child-name="{{ child_name }}"></div>
<link rel="stylesheet" href="/static/player.css">
<script type="module" src="/static/player.js"></script>
```

Move existing styling and behavior without changing interaction payloads.

- [ ] **Step 4: Run contract and existing session tests**

Run: `.venv/bin/python -m pytest tests/test_player_contract.py tests/test_session_loop.py -q`

Expected: PASS with all existing `choice`, `voice`, callback, and entry-source assertions intact.

- [ ] **Step 5: Commit**

```bash
git add demo/static/player.css demo/static/player.js demo/templates/player.html demo/web.py tests/test_player_contract.py
git commit -m "refactor: extract story player static modules"
```

---

### Task 3: Implement an explicit retryable player state machine

**Files:**
- Modify: `demo/static/player.js`
- Modify: `demo/templates/player.html`
- Create: `scripts/browser_resilience.py`
- Test: `tests/test_player_contract.py`

- [ ] **Step 1: Specify the state vocabulary in a failing source contract**

```python
def test_player_defines_explicit_states():
    source = Path("demo/static/player.js").read_text()
    for state in ("idle", "starting", "playing", "submitting", "recoverable_error", "complete"):
        assert f'"{state}"' in source
```

- [ ] **Step 2: Run the test and confirm failure**

Run: `.venv/bin/python -m pytest tests/test_player_contract.py::test_player_defines_explicit_states -q`

Expected: FAIL before the state vocabulary exists.

- [ ] **Step 3: Add the minimal state controller**

```javascript
const State = Object.freeze({
  IDLE: "idle", STARTING: "starting", PLAYING: "playing",
  SUBMITTING: "submitting", ERROR: "recoverable_error", COMPLETE: "complete",
});

function transition(next, message = "") {
  state = next;
  document.body.dataset.playerState = next;
  retryButton.hidden = next !== State.ERROR;
  status.textContent = message;
  for (const control of document.querySelectorAll("button,input")) {
    control.disabled = next === State.STARTING || next === State.SUBMITTING;
  }
}
```

Store the failed operation as a closure and run it only from the explicit retry button. Advance `idx` only after `response.ok`; never advance on network rejection, 4xx, or 5xx.

- [ ] **Step 4: Add browser failure scenarios**

In `scripts/browser_resilience.py`, use Playwright routing to fail the first start and first interaction request:

```python
page.route("**/api/v1/session/start", fail_once_then_continue)
page.click("#start-btn")
expect(page.locator("body")).to_have_attribute("data-player-state", "recoverable_error")
page.click("#retry-btn")
expect(page.locator("body")).to_have_attribute("data-player-state", "playing")
```

Also double-click the first choice and assert only one matching `session.interaction` is persisted.

- [ ] **Step 5: Run browser and unit checks**

Run:

```bash
.venv/bin/python -m pytest tests/test_player_contract.py tests/test_session_loop.py -q
.venv/bin/python scripts/browser_resilience.py
```

Expected: PASS; no JavaScript page errors and one accepted event per action.

- [ ] **Step 6: Commit**

```bash
git add demo/static/player.js demo/templates/player.html scripts/browser_resilience.py tests/test_player_contract.py
git commit -m "feat: make player actions retryable and touch safe"
```

---

### Task 4: Build the responsive forest stage and bounded motion system

**Files:**
- Create: `assets/environment/forest/background.svg`
- Create: `assets/environment/forest/foreground.svg`
- Create: `assets/character/doudou/action/idle.svg`
- Create: `assets/character/doudou/action/celebrate.svg`
- Create: `assets/character/doudou/emotion/curious.svg`
- Create: `demo/static/asset-manifest.json`
- Modify: `demo/static/player.css`
- Modify: `demo/static/player.js`
- Test: `tests/test_player_contract.py`

- [ ] **Step 1: Add a failing manifest completeness test**

```python
import json
from pathlib import Path


def test_visual_manifest_contains_reviewed_states():
    manifest = json.loads(Path("demo/static/asset-manifest.json").read_text())
    required = {"idle", "appear", "explore", "curious", "celebrate", "farewell"}
    assert required <= manifest["doudou"].keys()
    for path in manifest["doudou"].values():
        assert Path(path.removeprefix("/assets/")).with_stem(Path(path).stem)
        assert Path("assets", path.removeprefix("/assets/")).exists()
```

- [ ] **Step 2: Run the test and confirm the missing manifest fails**

Run: `.venv/bin/python -m pytest tests/test_player_contract.py::test_visual_manifest_contains_reviewed_states -q`

Expected: FAIL because the manifest does not exist.

- [ ] **Step 3: Add reviewed assets and semantic mapping**

Use this exact manifest shape:

```json
{
  "forest": {
    "background": "/assets/environment/forest/background.svg",
    "foreground": "/assets/environment/forest/foreground.svg"
  },
  "doudou": {
    "idle": "/assets/character/doudou/action/idle.svg",
    "appear": "/assets/character/doudou/action/appear.svg",
    "explore": "/assets/character/doudou/action/explore.svg",
    "curious": "/assets/character/doudou/emotion/curious.svg",
    "celebrate": "/assets/character/doudou/action/celebrate.svg",
    "farewell": "/assets/character/doudou/action/wave.svg"
  }
}
```

Every SVG must preserve the Character Bible features: cream body, light-brown inner ears, pink nose, notch in the left ear, and green scarf.

- [ ] **Step 4: Add responsive and accessibility rules**

```css
#stage { width:min(100vw, 768px); min-height:100svh; padding:clamp(12px,3vw,28px); }
.choice-btn { min-height:56px; min-width:180px; touch-action:manipulation; }
@media (max-width:430px) { #doudou { width:min(52vw,220px); } .bubble { font-size:18px; } }
@media (prefers-reduced-motion:reduce) { *,*::before,*::after { animation-duration:1ms!important; transition-duration:1ms!important; } }
```

- [ ] **Step 5: Verify visual states at two viewports**

Extend `scripts/browser_walk.py` to capture `/tmp/player-phone.png` at 390×844 and `/tmp/player-tablet.png` at 768×1024, and assert no horizontal overflow:

```python
assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
```

Expected: both screenshots contain the full speech bubble and primary action.

- [ ] **Step 6: Commit**

```bash
git add assets demo/static/asset-manifest.json demo/static/player.css demo/static/player.js scripts/browser_walk.py tests/test_player_contract.py
git commit -m "feat: add responsive forest experience"
```

---

### Task 5: Add the fixed `doudou_v1` voice catalog

**Files:**
- Create: `runtime/voice/__init__.py`
- Create: `runtime/voice/catalog.py`
- Create: `assets/audio/doudou_v1/manifest.yaml`
- Modify: `runtime/story/emitter.py`
- Test: `tests/test_voice.py`

- [ ] **Step 1: Write failing voice catalog tests**

```python
from runtime.voice.catalog import clip_key, voice_metadata


def test_clip_key_is_stable_and_versioned():
    assert clip_key("明天见！", "doudou_v1") == clip_key("明天见！", "doudou_v1")
    assert clip_key("明天见！", "doudou_v1") != clip_key("明天见", "doudou_v1")


def test_unknown_voice_fails_closed():
    import pytest
    with pytest.raises(ValueError, match="unsupported voice"):
        voice_metadata("你好", "someone_else")
```

- [ ] **Step 2: Run and verify the import failure**

Run: `.venv/bin/python -m pytest tests/test_voice.py -q`

Expected: FAIL because `runtime.voice` does not exist.

- [ ] **Step 3: Implement deterministic lookup**

```python
from hashlib import sha256

VOICE_VERSION = "doudou_v1"


def clip_key(text: str, voice: str = VOICE_VERSION) -> str:
    if voice != VOICE_VERSION:
        raise ValueError(f"unsupported voice: {voice}")
    digest = sha256(f"{voice}\0{text}".encode()).hexdigest()[:16]
    return f"{voice}/{digest}.mp3"


def voice_metadata(text: str, voice: str = VOICE_VERSION) -> dict:
    key = clip_key(text, voice)
    return {"voice": voice, "audio_url": f"/assets/audio/{key}"}
```

Add optional `audio_url` to dialogue nodes in `schemas/scene-dsl.schema.json` and emit it beside the existing fixed `voice` field. The contract remains valid when `audio_url` is absent.

- [ ] **Step 4: Add the reviewed trial clip manifest**

The YAML manifest must list each exact authored dialogue text, its `clip_key`, reviewer, and `character_bible_version: "1.0"`. Do not add voice cloning or arbitrary user-text synthesis.

- [ ] **Step 5: Run voice, schema, and emitter tests**

Run: `.venv/bin/python -m pytest tests/test_voice.py tests/test_story.py tests/test_contracts.py -q`

Expected: PASS; every emitted dialogue uses `doudou_v1`, and missing audio remains schema-valid.

- [ ] **Step 6: Commit**

```bash
git add runtime/voice runtime/story/emitter.py schemas/scene-dsl.schema.json assets/audio/doudou_v1/manifest.yaml tests/test_voice.py tests/test_story.py
git commit -m "feat: add bounded doudou voice catalog"
```

---

### Task 6: Implement deterministic audio fallback and pacing

**Files:**
- Modify: `demo/static/player.js`
- Modify: `demo/static/player.css`
- Modify: `scripts/browser_resilience.py`
- Test: `tests/test_player_contract.py`

- [ ] **Step 1: Add source contracts for audio fallback and pacing**

```python
def test_player_has_audio_fallback_and_pacing_hooks():
    source = Path("demo/static/player.js").read_text()
    assert "playDialogue" in source
    assert "audio.play()" in source
    assert "Promise.all" in source
    assert "sound-enable" in source
```

- [ ] **Step 2: Run and confirm failure**

Run: `.venv/bin/python -m pytest tests/test_player_contract.py::test_player_has_audio_fallback_and_pacing_hooks -q`

Expected: FAIL before audio handling exists.

- [ ] **Step 3: Implement text-first playback**

```javascript
async function playDialogue(node) {
  bubble.textContent = node.text;
  const minimum = new Promise(resolve => setTimeout(resolve, Math.max(900, node.text.length * 90)));
  const spoken = node.audio_url ? playClip(node.audio_url).catch(() => showSoundEnable()) : Promise.resolve();
  await Promise.all([minimum, spoken]);
  nextBtn.hidden = false;
}
```

`playClip` must resolve on `ended`, reject on `error` or blocked `play()`, and never prevent text from appearing. The sound-enable control retries the current clip only after an explicit tap.

- [ ] **Step 4: Add browser scenarios**

Abort all `**/*.mp3` requests and assert the dialogue and next button still appear. In a second scenario, fulfill an MP3 request and assert the next button stays hidden until both minimum display time and audio completion.

- [ ] **Step 5: Run browser resilience checks**

Run: `.venv/bin/python scripts/browser_resilience.py`

Expected: PASS for audio available, missing, and autoplay-blocked cases.

- [ ] **Step 6: Commit**

```bash
git add demo/static/player.js demo/static/player.css scripts/browser_resilience.py tests/test_player_contract.py
git commit -m "feat: add doudou audio fallback and pacing"
```

---

### Task 7: Define the minimum multi-day trial content matrix

**Files:**
- Create: `world-model/trial-content.yaml`
- Create: `runtime/story/trial_content.py`
- Modify: `demo/engine.py`
- Test: `tests/test_trial_content.py`

- [ ] **Step 1: Write failing continuity tests**

```python
from runtime.story.trial_content import load_trial_content


def test_trial_content_covers_fourteen_days_without_dead_callbacks():
    days = load_trial_content()
    assert [item["day"] for item in days] == list(range(1, 15))
    moments = {item["callback_offer"] for item in days if item.get("callback_offer")}
    references = {item["callback_reference"] for item in days if item.get("callback_reference")}
    assert references <= moments
    assert all(item["duration_minutes"] <= 8 for item in days)
```

- [ ] **Step 2: Run and confirm failure**

Run: `.venv/bin/python -m pytest tests/test_trial_content.py -q`

Expected: FAIL because no trial matrix exists.

- [ ] **Step 3: Author the bounded matrix**

Each of the 14 YAML entries must contain:

```yaml
- day: 1
  template_id: explore_hidden_clues
  duration_minutes: 6
  emotional_beat: 豆豆兔第一次请孩子帮忙
  callback_offer: 第一次找到发光叶子
  callback_reference: null
```

Days 2–14 must reference only a prior offered moment, rotate existing template categories, and retain one continuing story thread. Keep each session at 5–8 minutes and do not introduce scores or completion rewards.

- [ ] **Step 4: Select trial content only for explicitly enrolled participants**

Add `trial_day: int | None = None` to the session-start orchestration path. When absent, retain current deterministic behavior. When present, load the matching bounded entry and attach `trial_day` and `trial_content_version` to `session.started`.

- [ ] **Step 5: Run content and regression tests**

Run: `.venv/bin/python -m pytest tests/test_trial_content.py tests/test_session_loop.py tests/test_adventure_templates.py -q`

Expected: PASS, with existing virtual-child behavior unchanged outside trial mode.

- [ ] **Step 6: Commit**

```bash
git add world-model/trial-content.yaml runtime/story/trial_content.py demo/engine.py tests/test_trial_content.py tests/test_session_loop.py
git commit -m "feat: add bounded multi-day trial content"
```

---

### Task 8: Add stable experiment enrollment and readiness projection

**Files:**
- Create: `runtime/metrics/readiness.py`
- Modify: `demo/web.py`
- Modify: `demo/templates/index.html`
- Test: `tests/test_readiness.py`
- Test: `tests/test_session_loop.py`

- [ ] **Step 1: Write failing readiness projection tests**

```python
from runtime.metrics.readiness import readiness_view


def test_readiness_flags_preview_only_data():
    events = [{"event_type": "session.started", "payload": {
        "date": "2026-07-27", "launch_source": "parent_preview", "session_id": "s1"}}]
    view = readiness_view(events)
    assert view["child_session_days"] == 0
    assert view["warnings"] == ["no_child_mode_sessions"]


def test_readiness_never_exposes_performance_metrics():
    view = readiness_view([])
    assert "completion_rate" not in view
    assert "learning_minutes" not in view
```

- [ ] **Step 2: Run and verify import failure**

Run: `.venv/bin/python -m pytest tests/test_readiness.py -q`

Expected: FAIL because `readiness_view` does not exist.

- [ ] **Step 3: Implement a read-only projection**

Return this stable shape:

```python
{
    "child_session_days": int,
    "d2_returned": bool | None,
    "active_days_d7": float,
    "active_days_d14": float,
    "adventure_continuation": int,
    "callback_recognition_rate": float | None,
    "last_child_session_date": str | None,
    "warnings": list[str],
}
```

Build it from `relationship_metrics` plus data-health checks; do not write events.

- [ ] **Step 4: Add server-side enrollment tokens**

Create `POST /api/v1/trial/enroll` for the local adult dashboard. Persist a random opaque token mapped to `child_id`, enrollment date, and content version. Add `GET /trial/{token}` that issues a `child_mode` entry server-side and redirects to `/player`; unknown tokens return 404. Never accept `launch_source` from the client.

- [ ] **Step 5: Render readiness cards**

Show only the stable projection fields and warnings in `index.html`. Label preview sessions as excluded. Preserve the existing growth cards, but visually separate them from the Phase 0 experiment block.

- [ ] **Step 6: Verify isolation and endpoint behavior**

Run: `.venv/bin/python -m pytest tests/test_readiness.py tests/test_metrics.py tests/test_session_loop.py -q`

Expected: PASS; forged token is 404, preview events do not change readiness metrics, and enrolled child sessions remain `child_mode`.

- [ ] **Step 7: Commit**

```bash
git add runtime/metrics/readiness.py demo/web.py demo/templates/index.html tests/test_readiness.py tests/test_session_loop.py
git commit -m "feat: add trial enrollment and readiness view"
```

---

### Task 9: Build the internal readiness gate

**Files:**
- Create: `scripts/trial_readiness.py`
- Create: `docs/trial/acceptance-checklist.md`
- Modify: `scripts/browser_walk.py`
- Modify: `scripts/browser_resilience.py`

- [ ] **Step 1: Add the gate runner**

The runner must execute these commands and stop at the first failure:

```python
CHECKS = [
    [".venv/bin/python", "-m", "pytest", "-q"],
    [".venv/bin/ruff", "check", "."],
    [".venv/bin/python", "scripts/browser_walk.py"],
    [".venv/bin/python", "scripts/browser_resilience.py"],
]
```

Print one final machine-readable line:

```text
TRIAL_READINESS=PASS
```

Never print PASS if a subprocess is skipped or cannot run.

- [ ] **Step 2: Write the manual device checklist**

The checklist must require signed results for:

```markdown
- [ ] 390×844 phone: no overflow; child completes without adult navigation
- [ ] 768×1024 tablet: primary controls stay within reach
- [ ] Rapid double taps create one accepted interaction
- [ ] Wi-Fi interruption offers retry and does not advance
- [ ] Sound blocked/muted still leaves a complete text journey
- [ ] Doudou assets match Character Bible 1.0
- [ ] `/preview` activity is absent from child relationship metrics
- [ ] Session lasts 5–8 minutes with no dead end
```

- [ ] **Step 3: Run the complete automated gate**

Run: `.venv/bin/python scripts/trial_readiness.py`

Expected: final line `TRIAL_READINESS=PASS`.

- [ ] **Step 4: Perform and sign manual acceptance**

Record date, reviewer, device/browser versions, result, and links to the phone/tablet screenshots in `docs/trial/acceptance-checklist.md`. Any failed item returns work to its owning P1–P5 task.

- [ ] **Step 5: Commit**

```bash
git add scripts/trial_readiness.py scripts/browser_walk.py scripts/browser_resilience.py docs/trial/acceptance-checklist.md
git commit -m "test: add child trial readiness gate"
```

---

### Task 10: Run and review the 7–14 day child trial

**Files:**
- Create: `docs/trial/protocol.md`
- Create: `docs/trial/results/YYYY-MM-DD-phase-0-trial.md`
- Modify: `docs/next-steps.md`

- [ ] **Step 1: Freeze the protocol before enrollment**

Document these fields explicitly:

```markdown
Participant: one child aged 4–6, guardian consent recorded outside the event log
Duration: minimum 7, maximum 14 calendar days
Exposure: one optional invitation per day; no completion pressure
Primary: d2_returned, active_days_d7, active_days_d14
Supporting: adventure_continuation, callback_recognition_rate
Stop: child distress, guardian withdrawal, unsafe content, identity/data contamination
```

- [ ] **Step 2: Run the readiness gate immediately before enrollment**

Run: `.venv/bin/python scripts/trial_readiness.py`

Expected: `TRIAL_READINESS=PASS`. Do not enroll on any other result.

- [ ] **Step 3: Enroll and record the immutable baseline**

Record commit SHA, content version, Character Bible version, participant token suffix, start date, and expected review date. Do not store child PII in Git or the event log.

- [ ] **Step 4: Perform daily data-health checks without prompting outcomes**

Check that events are attributable to the enrolled child entry, preview events remain excluded, and callbacks obey shown-before-answered. Do not coach the child to return or recognize a callback.

- [ ] **Step 5: Write the result report**

Use this result table:

```markdown
| Metric | Result | Interpretation |
|---|---:|---|
| d2_returned | true/false | Did the child return the next calendar day? |
| active_days_d7 | 0.0000–1.0000 | Active child-mode days / available D7 days |
| active_days_d14 | 0.0000–1.0000 | Active child-mode days / available D14 days |
| adventure_continuation | integer | Next-day returns to the same arc |
| callback_recognition_rate | 0.0000–1.0000 or null | Recognized / offered callbacks |
```

Conclude with exactly one recommendation: repeat Phase 0, refine experience and repeat, or advance to Phase 1. Include evidence and uncertainty; do not infer learning gains.

- [ ] **Step 6: Update roadmap status and commit**

```bash
git add docs/trial/protocol.md docs/trial/results docs/next-steps.md
git commit -m "docs: record phase 0 child trial result"
```

---

## Final verification

- [ ] Run the entire Python suite: `.venv/bin/python -m pytest -q`
- [ ] Run lint: `.venv/bin/ruff check .`
- [ ] Run browser happy path: `.venv/bin/python scripts/browser_walk.py`
- [ ] Run browser failure paths: `.venv/bin/python scripts/browser_resilience.py`
- [ ] Run readiness gate: `.venv/bin/python scripts/trial_readiness.py`
- [ ] Confirm `git status --short` contains only the signed manual checklist or trial result intended for the next commit.

Expected automated baseline before trial: 159 existing tests remain green plus all new tests; Ruff passes; final gate prints `TRIAL_READINESS=PASS`.
