# Referral Dashboard

SolarSquare's Referral sales-channel performance dashboard — funnel tracking (BQL →
MS → MD → Order → HOTO), MOP-vs-actual, city/sub-channel breakdowns, cohort and
velocity analysis. Also covers the Digital channel and a Ref-vs-Digital comparison
view in the same file, plus a separate Customer App login-tracking branch.

## What's in the dashboard

Four channels, picked from the switcher in the top bar:

- **Referral**: Executive Summary, MOP vs MTD, Actuals vs MOP, Last Month
  Performance, India Summary, City Summary, Sub-Channel, Effort and M0 funnels, BQL
  Quality, Velocity, WoW, Day on Day (counts and funnel), MoM Cohort, City MoM, City Deep
  Dive, Insights, Action Recommended. The four MOP tabs have their own 5-way target
  split (Sales / Non-Sales / BTL / Sales + Non-Sales / All).
- **Digital** and **Ref vs Digital**: being phased out eventually, no timeline.
- **Customer App**: Overview, MoM Trend, Login Velocity, Day on Day.

The Referral views carry a running FY27 tracker against the 40,000-HOTO target.

Cities are grouped into **6 tiers** — Focus, Big, Mid, Small, New, Expansion (in that
sort order) — defined by the `TIERS` constant in `index.html`, which is the source of
truth for the list. The **New** tier was added 2026-09-22; see `CLAUDE.md` Section 6.

For full business logic, terminology, calculation rules, and open items, see
[`CLAUDE.md`](CLAUDE.md) — that file is the detailed source of truth for this project
and is kept in sync with the code. This README is just an orientation.

**Picking this project back up (including in a new Claude Code session)?** Read
`CLAUDE.md`'s **Section 0 (CURRENT STATUS)** first — it's a living snapshot of exactly
what's done, what's mid-review, and what to do next, kept up to date as work progresses.

## Structure

- `index.html` — the entire dashboard (single file, no build step). Open it directly
  or serve it statically (currently GitHub Pages).
- `Referral Dashboard.gs` — Google Apps Script (v5). Queries BigQuery
  (`presales-442917.leadcsv.Samagam`) for both Referral and Digital channels, effort-level
  and lead-level, and pushes the resulting JSON straight to this repo's `main` branch via
  the GitHub API. This is the only data pipeline — run it on a time-based trigger, not
  manually (manual Apps Script runs are capped at 6 min; the trigger gets 30 min).
- `data/` (~100 MB) — the JSON files the Apps Script produces, read directly by `index.html`:
  `referral_effort.json`, `referral_leads.json`, `digital_effort.json`,
  `digital_leads.json`, plus `referral_mop.json` (MOP targets, maintained separately —
  see `scripts/build_mop_json.py` below; it won't have every city, and that's
  expected for Expansion-tier cities without a monthly MOP).
- `data/referral_mop_history.json` — every past month's MOP, keyed by month, each
  carrying the list of splits that month has targets for. Written by
  `build_mop_json.py` alongside the flat current-month file (which only ever holds
  the running month and is overwritten each time a workbook lands). This is what
  the "Last Month Performance" tab compares a closed month against; seeded from
  git history by `scripts/backfill_mop_history.py`.
- `scripts/build_mop_json.py` — regenerates `data/referral_mop.json` from the monthly
  `MOP <Mon> Referral.xlsx` workbook. Since Sep'26 that workbook splits targets 3 ways
  by sub-channel group (Sales / Non-Sales / BTL) plus two roll-ups, which is too many
  numbers to retype by hand. Run
  `python scripts/build_mop_json.py "Referrals MOP - Oct'26.xlsx"`
  (add `--dry-run` to inspect first). It validates the workbook's column layout before
  trusting it, and reports rather than silently reconciling the source's own rounding
  drift between `Total (Sales+Non-Sales)` and `Sales + Non Sales`. Pass
  `--month YYYY-MM` if the targets are not for the current calendar month.
  A month can be revised mid-month — Sep'26 was, on 2026-09-21 — so re-running it
  for a month already present is expected: it overwrites the flat current-month
  file and replaces just that month's entry in the history file, leaving the other
  months alone, and prints the India BQL before/after so the change is visible.
- `scripts/backfill_mop_history.py` — one-off/re-runnable seed of the history file
  from past versions of `referral_mop.json` in git. Only Jul/Aug/Sep '26 are
  recoverable: June and earlier predate the explicit Order target, and the whole
  analysis is an Order-deficit decomposition.
- `signals.preview.html` — **work in progress, gitignored, not live.** "Signals", a
  separate page that ranks what is moving against this month's MOP by orders at
  risk and turns each signal into a downloadable worklist. Once approved it ships
  as `signals.html` next to `index.html` (same GitHub Pages site). See `CLAUDE.md`
  Section 0a, 2026-09-08.
- `.github/workflows/pull_customer_app.yml` — runs the Customer App puller 4x/day
  (9am / 3pm / 6pm / 9pm IST) and commits `data/customer_app.json` if it changed.
  Needs the `METABASE_API_KEY` repo secret.
- `.github/workflows/test.yml` — placeholder, does not run tests.
- `preview-local.bat` — double-click to preview the dashboard locally on Windows.
  Starts a local server on `http://localhost:8743` and opens it in your browser.
  Opens `index.preview.html` if one exists (a work-in-progress copy under review),
  otherwise `index.html`. Necessary because opening the file directly (double-click,
  no server) makes it fall back to fetching data from the live GitHub Pages site
  instead of your local files — this script is what lets you actually preview local
  changes, including data files, before they're pushed.

### Customer App branch (new, separate from everything above)

A second, independent data pipeline and dashboard branch, tracking Customer App login
behavior against project lifecycle milestones. Sourced from **Metabase** (Postgres), not
BigQuery — entirely unrelated to the Apps Script pipeline above. See `CLAUDE.md` Section
15 for the full write-up (business logic, data model, what's built vs pending).

- `scripts/customer_app_query.sql` — the query (also usable standalone in Metabase).
- `scripts/pull_customer_app.py` — the puller. Runs on a schedule via the workflow
  above; to run by hand: `python scripts/pull_customer_app.py`. Locally it needs
  `.metabase_key/metabase_key.txt` (gitignored, not in this repo; ask Yash for the
  API key if it's missing). It refuses to overwrite the data file if a pull comes
  back empty or drops by more than 20% (set `ALLOW_DATA_DROP=1` when a drop is
  expected).
- `data/customer_app.json` — the pulled data, one row per project.

## Deployment

Live at **https://yashk-sse.github.io/Referral-Dashboard/** via GitHub Pages, from this
repo (`yashk-SSE/Referral-Dashboard`) — switched from Netlify due to its free-tier
monthly production-deploy cap. Pushing to `main` (whether from the Apps Script or
manually) triggers a redeploy.
