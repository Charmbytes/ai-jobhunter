"""Local persistence for applied-job history and saved searches.

Stored as a single JSON file at ~/.jobhunter/state.json so it survives across
runs. Writes are atomic (temp file + replace)."""
from __future__ import annotations

import json
import os
import time
import uuid

STATE_DIR = os.path.expanduser("~/.jobhunter")
STATE_FILE = os.path.join(STATE_DIR, "state.json")

_DEFAULT = {"applied": {}, "saved_searches": []}


def _load() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            data.setdefault("applied", {})
            data.setdefault("saved_searches", [])
            return data
        except Exception:  # noqa: BLE001  (corrupt file -> start fresh)
            pass
    return {"applied": {}, "saved_searches": []}


def _save(state: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)


# ---------- applied jobs ----------
def list_applied() -> dict:
    return _load()["applied"]


def applied_uids() -> set[str]:
    return set(_load()["applied"].keys())


def mark_applied(jobs: list[dict]) -> dict:
    """jobs: list of dicts that include at least 'uid'."""
    state = _load()
    for j in jobs:
        uid = j.get("uid")
        if not uid:
            continue
        state["applied"][uid] = {
            "uid": uid,
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "url": j.get("url", ""),
            "source": j.get("source", ""),
            "applied_at": time.time(),
        }
    _save(state)
    return state["applied"]


def unmark_applied(uid: str) -> dict:
    state = _load()
    state["applied"].pop(uid, None)
    _save(state)
    return state["applied"]


# ---------- saved searches ----------
def list_searches() -> list[dict]:
    return _load()["saved_searches"]


def add_search(name: str, payload: dict) -> dict:
    state = _load()
    item = {
        "id": uuid.uuid4().hex[:8],
        "name": name or "Untitled search",
        "created_at": time.time(),
        "payload": payload,
    }
    state["saved_searches"].append(item)
    _save(state)
    return item


def delete_search(sid: str) -> list[dict]:
    state = _load()
    state["saved_searches"] = [s for s in state["saved_searches"] if s["id"] != sid]
    _save(state)
    return state["saved_searches"]
