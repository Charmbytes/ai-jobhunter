"""Human-in-the-loop assisted apply.

Design choice (read this): we do NOT mass auto-submit applications to
LinkedIn / Naukri / Internshala. Doing so violates their Terms of Service and
gets accounts banned — a real risk while you're job hunting — and produces
low-quality spray-and-pray applications. Instead this opens each approved job
in YOUR own logged-in browser session and pauses so you review and click the
final submit yourself.

It uses a persistent Chromium profile, so you log in once and stay logged in
across runs. An optional autofill hook is provided as a clearly-marked stub you
can customize per site — it is OFF by default and never clicks "submit".

Requires:  pip install playwright  &&  playwright install chromium
"""
from __future__ import annotations

import os

from .models import Job, UserProfile

PROFILE_DIR = os.path.expanduser("~/.jobhunter/browser_profile")


def _lazy_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: WPS433
        return sync_playwright
    except ImportError:
        return None


def autofill_hint(page, profile: UserProfile) -> None:
    """OPTIONAL best-effort form helper. Fills only obvious generic fields and
    NEVER submits. Customize selectors per site as needed. Off by default."""
    try:
        for sel in ['input[type="email"]', 'input[name*="email" i]']:
            if page.locator(sel).count():
                page.fill(sel, profile.email)
                break
        for sel in ['input[type="tel"]', 'input[name*="phone" i]', 'input[name*="mobile" i]']:
            if page.locator(sel).count():
                page.fill(sel, profile.phone)
                break
    except Exception as e:  # noqa: BLE001
        print(f"  (autofill skipped: {e})")


def open_in_session(job_dicts: list[dict], autofill: bool = False) -> bool:
    """Web-platform apply path: open every approved job as a tab in your
    persistent, logged-in Chromium profile and leave the window open so you
    apply at your own pace. Non-interactive (no stdin), safe to run from a
    background thread. Returns False if Playwright isn't installed."""
    sync_playwright = _lazy_playwright()
    if sync_playwright is None:
        return False
    os.makedirs(PROFILE_DIR, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE_DIR, headless=False, viewport={"width": 1280, "height": 900}
        )
        first = ctx.pages[0] if ctx.pages else ctx.new_page()
        urls = [d["url"] for d in job_dicts if d.get("url")]
        if urls:
            try:
                first.goto(urls[0], wait_until="domcontentloaded", timeout=45000)
            except Exception:  # noqa: BLE001
                pass
            for u in urls[1:]:
                pg = ctx.new_page()
                try:
                    pg.goto(u, wait_until="domcontentloaded", timeout=45000)
                except Exception:  # noqa: BLE001
                    pass
        # keep the browser open until the user closes every tab
        try:
            while len(ctx.pages) > 0:
                ctx.pages[0].wait_for_timeout(1000)
        except Exception:  # noqa: BLE001
            pass
        try:
            ctx.close()
        except Exception:  # noqa: BLE001
            pass
    return True


def assisted_apply(jobs: list[Job], profile: UserProfile, autofill: bool = False) -> None:
    if not jobs:
        return
    sync_playwright = _lazy_playwright()
    if sync_playwright is None:
        print(
            "\nPlaywright isn't installed, so I can't open an assisted browser.\n"
            "Install it with:\n"
            "    pip install playwright\n"
            "    playwright install chromium\n\n"
            "For now, here are the approved job links to open manually:"
        )
        for j in jobs:
            print(f"  • {j.title} @ {j.company}\n    {j.url}")
        return

    os.makedirs(PROFILE_DIR, exist_ok=True)
    print(
        f"\nOpening {len(jobs)} approved job(s) in your browser session.\n"
        "First run: log in to the site when the window opens — you stay logged "
        "in for next time.\n"
        "For each job: review the page, fill what you want, click the site's own "
        "Apply/Submit button yourself, then return here and press Enter.\n"
    )

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE_DIR, headless=False, viewport={"width": 1280, "height": 900}
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for i, job in enumerate(jobs, 1):
            print(f"[{i}/{len(jobs)}] {job.title} @ {job.company}")
            try:
                page.goto(job.url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:  # noqa: BLE001
                print(f"  couldn't open ({e}); link: {job.url}")
                continue
            if autofill:
                autofill_hint(page, profile)
            input("  -> apply on the page, then press Enter for the next job… ")
        print("\nDone. Closing browser.")
        ctx.close()
