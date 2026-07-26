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

@app.post("/api/v1/session/start")
def session_start(child: str = Form(...), launch_source: str = Form("child_mode")):
    engine = engines[child]
    try:
        session = engine.start_session(launch_source=launch_source)
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
def doudou_request(child: str = Form(...), launch_source: str = Form("child_mode")):
    engines[child].request_doudou(launch_source=launch_source)
    return JSONResponse({"ok": True})


@app.get("/player", response_class=HTMLResponse)
def player(request: Request, child: str = "vc_curious"):
    """The CHILD entry — sessions from here count toward the North Star."""
    return templates.TemplateResponse(
        request,
        "player.html",
        {"child_id": child, "launch_source": "child_mode",
         "child_name": engines[child].child["name"] if child in engines else ""},
    )


@app.get("/preview", response_class=HTMLResponse)
def preview(request: Request, child: str = "vc_curious"):
    """The PARENT preview entry — same player, but sessions are honestly
    labelled parent_preview and never touch return-rate metrics."""
    return templates.TemplateResponse(
        request,
        "player.html",
        {"child_id": child, "launch_source": "parent_preview",
         "child_name": engines[child].child["name"] if child in engines else ""},
    )
