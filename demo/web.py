"""Demo web app — parent dashboard AND child Story Player (Phase 0).

Parent surface: child state + active arc + evidence + insights (/).
Child surface: /player — a minimal Story Player that consumes Scene DSL
nodes (ADR-014) and records REAL interaction events (session.started,
session.interaction, child.requested_doudou).

Run: python3 -m uvicorn demo.web:app --port 8765
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from demo.engine import ChildEngine

PROFILES = {
    "vc_curious": "demo/virtual_children/curious_low_persistence.yaml",
    "vc_language": "demo/virtual_children/language_strong_math_weak.yaml",
    "vc_coldstart": "demo/virtual_children/cold_start_newcomer.yaml",
    "vc_noise": "demo/virtual_children/noise_child.yaml",
}

app = FastAPI(title="AI Growth OS — Demo")
app.mount("/assets", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "assets")), name="assets")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
engines: dict[str, ChildEngine] = {}


@app.on_event("startup")
def startup() -> None:
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(exist_ok=True)
    for cid, path in PROFILES.items():
        # Persistent db per child: sessions and growth state survive restarts
        # (the event log is the system of record, ADR-016).
        engines[cid] = ChildEngine(path, db=f"demo/data/{cid}.db")


@app.get("/", response_class=HTMLResponse)
def index(request: Request, child: str = "vc_curious"):
    engine = engines.get(child) or engines["vc_curious"]
    return templates.TemplateResponse(
        request,
        "index.html",
        {"v": engine.view(), "child_id": engine.child_id,
         "children": {cid: e.child["name"] for cid, e in engines.items()}},
    )


@app.post("/submit")
def submit(
    child: str = Form(...),
    channel: str = Form(...),
    raw_text: str = Form(...),
    checkin_status: str = Form("completed"),
):
    engine = engines[child]
    engine.submit(channel, raw_text, checkin_status)
    return RedirectResponse(f"/?child={child}", status_code=303)


# -- Phase 0: session API + Story Player --------------------------------------

# Server-issued entry registry: the launch source is a SERVER-SIDE fact.
# /player issues child_mode entries, /preview issues parent_preview entries;
# clients can never claim a source — they present an entry id.
entries: dict[str, dict] = {}


def _issue_entry(child: str, source: str) -> str:
    import uuid
    entry_id = f"entry_{uuid.uuid4().hex[:10]}"
    entries[entry_id] = {"child": child, "launch_source": source}
    return entry_id


@app.post("/api/v1/session/start")
def session_start(child: str = Form(...), entry_id: str = Form(...)):
    entry = entries.get(entry_id)
    if not entry or entry["child"] != child:
        return JSONResponse(
            {"error": "unknown entry — open the player/preview page first"},
            status_code=403)
    engine = engines[child]
    try:
        session = engine.start_session(launch_source=entry["launch_source"])
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    return JSONResponse(session)


@app.post("/api/v1/session/interaction")
def session_interaction(
    child: str = Form(...),
    session_id: str = Form(...),
    node_type: str = Form(...),
    data: str = Form("{}"),
):
    import json

    from runtime.contracts import ContractViolation
    engine = engines[child]
    try:
        engine.record_interaction(session_id, node_type, json.loads(data))
    except ContractViolation as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    return JSONResponse({"ok": True})


@app.post("/api/v1/doudou/request")
def doudou_request(child: str = Form(...), session_id: str = Form(...)):
    """Source is derived from the session's own started event — same
    derivation as callbacks, never from the client."""
    engine = engines[child]
    from runtime.state.callbacks import session_launch_source
    source = session_launch_source(
        engine.store.events_for(child), session_id)
    if source is None:
        return JSONResponse({"error": "unknown session"}, status_code=403)
    engine.request_doudou(launch_source=source)
    return JSONResponse({"ok": True})


@app.get("/player", response_class=HTMLResponse)
def player(request: Request, child: str = "vc_curious"):
    """The CHILD entry — sessions from here count toward the North Star."""
    entry_id = _issue_entry(child, "child_mode")
    return templates.TemplateResponse(
        request,
        "player.html",
        {"child_id": child, "entry_id": entry_id,
         "child_name": engines[child].child["name"] if child in engines else ""},
    )


@app.get("/preview", response_class=HTMLResponse)
def preview(request: Request, child: str = "vc_curious"):
    """The PARENT preview entry — same player, but sessions are honestly
    labelled parent_preview and never touch return-rate metrics."""
    entry_id = _issue_entry(child, "parent_preview")
    return templates.TemplateResponse(
        request,
        "player.html",
        {"child_id": child, "entry_id": entry_id,
         "child_name": engines[child].child["name"] if child in engines else ""},
    )
