"""Local web platform for the job hunter.

Run:  python server.py   then open http://127.0.0.1:5050
It wraps the same pipeline (sources -> matching) and serves a dashboard.
"""
from __future__ import annotations

import os
import threading
import webbrowser

import yaml
from flask import Flask, jsonify, request, send_from_directory

from jobhunter.apply import open_in_session
from jobhunter.matching import filter_and_rank
from jobhunter.models import Filters
from jobhunter.sources import AdzunaSource, MockSource, RemotiveSource
from jobhunter import store

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ROOT, "config.yaml")
WEBUI = os.path.join(ROOT, "webui")

app = Flask(__name__, static_folder=None)


def load_config() -> dict:
    if os.path.exists(CONFIG):
        with open(CONFIG) as f:
            return yaml.safe_load(f) or {}
    return {}


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def job_to_dict(j) -> dict:
    return {
        "uid": j.uid,
        "title": j.title,
        "company": j.company,
        "location": j.location,
        "url": j.url,
        "description": (j.description or "").strip()[:600],
        "salary_str": j.salary_str(),
        "salary_min": j.salary_min,
        "experience_level": j.experience_level,
        "alignment": j.alignment,
        "score": j.score,
        "matched_skills": j.matched_skills,
        "missing_skills": j.missing_skills,
        "source": j.source,
        "posted": j.posted.isoformat() if j.posted else None,
    }


def build_sources(cfg: dict, use_mock: bool, remote_ok: bool):
    if use_mock:
        return [MockSource()]
    sources = []
    az = cfg.get("adzuna") or {}
    if az.get("app_id") and az.get("app_key"):
        sources.append(AdzunaSource(az["app_id"], az["app_key"], az.get("country", "in")))
    if remote_ok:
        sources.append(RemotiveSource())
    if not sources:
        sources.append(MockSource())
    return sources


@app.route("/")
def index():
    return send_from_directory(WEBUI, "index.html")


@app.route("/api/config")
def api_config():
    cfg = load_config()
    prof = cfg.get("profile") or {}
    f = cfg.get("filters") or {}
    az = cfg.get("adzuna") or {}
    return jsonify({
        "skills": prof.get("skills", ["python", "sql", "pandas", "machine learning"]),
        "filters": {
            "keywords": f.get("keywords", ["data", "python"]),
            "locations": f.get("locations", ["Mumbai", "Remote"]),
            "salary_min": f.get("salary_min", 0),
            "experience_levels": f.get("experience_levels", ["intern", "entry"]),
            "min_alignment": f.get("min_alignment", 0),
            "remote_ok": f.get("remote_ok", True),
            "max_days_old": f.get("max_days_old", 30),
        },
        "has_adzuna": bool(az.get("app_id") and az.get("app_key")),
        "has_playwright": playwright_available(),
    })


@app.route("/api/search", methods=["POST"])
def api_search():
    body = request.get_json(force=True) or {}
    skills = body.get("skills", [])
    filters = Filters(
        keywords=body.get("keywords", []),
        locations=body.get("locations", []),
        salary_min=body.get("salary_min") or None,
        experience_levels=body.get("experience_levels", []),
        min_alignment=body.get("min_alignment", 0),
        max_days_old=body.get("max_days_old", 30),
        remote_ok=body.get("remote_ok", True),
    )
    use_mock = bool(body.get("mock", False))
    cfg = load_config()
    sources = build_sources(cfg, use_mock, filters.remote_ok)

    all_jobs, per_source = [], {}
    for s in sources:
        got = s.fetch(filters, limit=body.get("limit", 50))
        per_source[s.name] = len(got)
        all_jobs.extend(got)

    ranked = filter_and_rank(all_jobs, skills, filters)

    applied = store.applied_uids()
    include_applied = bool(body.get("include_applied", False))
    dicts, hidden = [], 0
    for j in ranked:
        d = job_to_dict(j)
        d["applied"] = d["uid"] in applied
        if d["applied"] and not include_applied:
            hidden += 1
            continue
        dicts.append(d)

    avg = round(sum(d["alignment"] for d in dicts) / len(dicts), 1) if dicts else 0
    return jsonify({
        "jobs": dicts,
        "meta": {"count": len(dicts), "avg_alignment": avg,
                 "sources": per_source, "used_mock": use_mock,
                 "applied_hidden": hidden},
    })


@app.route("/api/applied", methods=["GET"])
def api_applied_list():
    items = sorted(store.list_applied().values(),
                   key=lambda x: x.get("applied_at", 0), reverse=True)
    return jsonify({"applied": items})


@app.route("/api/applied", methods=["POST"])
def api_applied_mark():
    body = request.get_json(force=True) or {}
    store.mark_applied(body.get("jobs", []))
    return jsonify({"count": len(store.list_applied())})


@app.route("/api/applied/<uid>", methods=["DELETE"])
def api_applied_unmark(uid):
    store.unmark_applied(uid)
    return jsonify({"count": len(store.list_applied())})


@app.route("/api/searches", methods=["GET"])
def api_searches_list():
    return jsonify({"searches": store.list_searches()})


@app.route("/api/searches", methods=["POST"])
def api_searches_add():
    body = request.get_json(force=True) or {}
    item = store.add_search(body.get("name", ""), body.get("payload", {}))
    return jsonify({"search": item})


@app.route("/api/searches/<sid>", methods=["DELETE"])
def api_searches_delete(sid):
    return jsonify({"searches": store.delete_search(sid)})


@app.route("/api/apply", methods=["POST"])
def api_apply():
    body = request.get_json(force=True) or {}
    jobs = body.get("jobs", [])
    if not playwright_available():
        return jsonify({"status": "no_playwright",
                        "links": [j.get("url") for j in jobs]})
    threading.Thread(target=open_in_session, args=(jobs,), daemon=True).start()
    return jsonify({"status": "launched", "count": len(jobs)})


def main():
    port = int(os.environ.get("PORT", 5050))
    url = f"http://127.0.0.1:{port}"
    if not os.path.exists(CONFIG):
        print("Note: no config.yaml found — the app will run in sample-data mode.")
    print(f"Job Hunter platform running at {url}  (Ctrl+C to stop)")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(port=port, debug=False)


if __name__ == "__main__":
    main()
