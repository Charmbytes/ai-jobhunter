# AI JobHunter

A local job/internship hunter I built because I was tired of scrolling through 300 listings on
Naukri to find the 5 I was actually qualified for. It pulls listings from a couple of sources,
scores them against your skills so the good matches float to the top, and lets you review and
approve jobs before doing anything else. It does not auto-apply for you — more on why below.

![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-0F7C66)
![MIT License](https://img.shields.io/badge/license-MIT-16302B)
![Flask](https://img.shields.io/badge/built%20with-Flask-0B5C4C)

## Why this exists

Most job boards rank by "recency" or "relevance," which in practice means you see everything and
have to do the filtering in your head, job by job. On the other end, there's a whole category of
auto-apply tools that will happily spam 200 applications a day on your behalf — until the site
notices and bans your account, and you're left with 200 applications you didn't actually mean to
send.

This is the middle ground: it scores every listing against your actual skills, shows you *why* it
scored that way (matched skills vs. missing ones, right there on the card), and stops before the
apply button. You click apply yourself, from your own logged-in session. Slower than a bot, but
your account doesn't get flagged and you're not sending a resume to a job you're 20% qualified for.

## What it does

- **Fit scoring** — each listing gets a 0–100 score based on skill overlap with your profile.
  Not a black box — you can see exactly which required skills you have and which you're missing.
- **Filtering** — keyword/role, location (remote included), minimum salary, experience level, and
  a minimum fit score so you're not even shown the bad matches.
- **Review queue** — swipe through listings, approve the ones you want, they collect in a pipeline
  drawer so you're not hunting for them again later.
- **Assisted apply** — approved jobs open in a real, logged-in browser session (via Playwright) so
  you do the actual applying. Nothing gets auto-submitted.
- **Applied tracking** — once you've applied somewhere it's logged and won't show up again in
  future searches. You can unmark it if that was a mistake.
- **Saved searches** — save a filter combo, re-run it later without rebuilding it.
- **Sources** — Adzuna (free tier, works for India and internationally) and Remotive (remote jobs,
  no API key needed). Adding another source is one small class, described below.

## Getting it running

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional but recommended — copy the config and add your skills and an Adzuna key:

```bash
cp config.example.yaml config.yaml   # Windows: copy config.example.yaml config.yaml
```

Adzuna keys are free, sign up takes about a minute: https://developer.adzuna.com/. If you skip
this step the app still runs, just on sample data plus whatever Remotive returns.

```bash
python server.py
```

That serves the dashboard at `http://127.0.0.1:5050`.

If you just want to poke at the UI without installing anything, open `webui/preview.html`
directly in a browser — it's a static mock with sample data baked in.

### Assisted apply setup

This part's optional, only needed if you want the "open in browser" apply flow:

```bash
pip install playwright
playwright install chromium
```

First time you use it you'll need to log in to whatever site it opens. After that the session
sticks around so you don't have to log in every time.

## CLI, if you'd rather not use the browser

```bash
python -m jobhunter.main --mock --no-apply   # sample data, no live calls
python -m jobhunter.main                     # real run, reads config.yaml
```

## Roughly how it's wired together

```
sources (adzuna, remotive, ...)
   -> matching (skill detection, scoring, filtering)
   -> review (approve via UI or CLI)
   -> apply (opens in your browser, you click apply)
```

Applied history and saved searches get written to `~/.jobhunter/state.json`. Delete that file if
you ever want a clean slate.

## Layout

```
jobhunter/
├─ server.py              Flask app, dashboard + API
├─ webui/
│  ├─ index.html          the actual dashboard
│  └─ preview.html        standalone demo, no server
├─ jobhunter/
│  ├─ models.py           Job / UserProfile / Filters
│  ├─ matching.py         scoring + ranking logic
│  ├─ store.py            applied history, saved searches
│  ├─ review.py           CLI approval flow
│  ├─ apply.py            browser-based apply
│  ├─ main.py             CLI entry point
│  └─ sources/            adzuna, remotive, mock, + yours
├─ config.example.yaml
└─ requirements.txt
```

## Adding a source

Subclass `JobSource`, implement `fetch()` returning a list of `Job` objects, register it in
`build_sources()`. Matching and review pick it up without any other changes.

## On LinkedIn / Naukri / Internshala scraping

I didn't build scrapers for these on purpose. Scraping them or auto-submitting applications
violates their ToS and gets accounts banned pretty fast — I've seen it happen to people. Adzuna
covers a lot of the same listings legally, and for the actual apply step your own browser session
is what's used, so you're never at risk of a ban from this tool. Feel free to extend it if you
want to take that risk yourself, but it's not something I'm going to add support for here.

## License

MIT, see [LICENSE](LICENSE).
