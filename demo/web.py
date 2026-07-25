"""Parent-facing demo web app (Q2: minimal web, form B).

Single page: child state + active growth arc + evidence submission + event
feed. All data flows through the real pipeline via ChildEngine — what you
see is what the runtime computed, not a mock UI.

Run: python3 -m uvicorn demo.web:app --port 8765
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
engines: dict[str, ChildEngine] = {}


@app.on_event("startup")
def startup() -> None:
    for cid, path in PROFILES.items():
        engines[cid] = ChildEngine(path)


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
