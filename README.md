# Referral Dashboard

SolarSquare's Referral sales-channel performance dashboard — funnel tracking (BQL →
MS → MD → Order → HOTO), MOP-vs-actual, city/sub-channel breakdowns, cohort and
velocity analysis. Also covers the Digital channel and a Ref-vs-Digital comparison
view in the same file.

For full business logic, terminology, calculation rules, and open items, see
[`CLAUDE.md`](CLAUDE.md) — that file is the detailed source of truth for this project
and is kept in sync with the code. This README is just an orientation.

## Structure

- `index.html` — the entire dashboard (single file, no build step). Open it directly
  or serve it statically (currently GitHub Pages).
- `Referral Dashboard.gs` — Google Apps Script (v5). Queries BigQuery
  (`presales-442917.leadcsv.Samagam`) for both Referral and Digital channels, effort-level
  and lead-level, and pushes the resulting JSON straight to this repo's `main` branch via
  the GitHub API. This is the only data pipeline — run it on a time-based trigger, not
  manually (manual Apps Script runs are capped at 6 min; the trigger gets 30 min).
- `data/` — the JSON files the Apps Script produces, read directly by `index.html`:
  `referral_effort.json`, `referral_leads.json`, `digital_effort.json`,
  `digital_leads.json`, plus `referral_mop.json` (MOP targets, maintained separately —
  edit this file directly in GitHub each month; it won't have every city, and that's
  expected for Expansion-tier cities without a monthly MOP).
- `.github/workflows/test.yml` — placeholder, does not run tests.
- `preview-local.bat` — double-click to preview the dashboard locally on Windows.
  Starts a local server on `http://localhost:8743` and opens it in your browser.
  Opens `index.preview.html` if one exists (a work-in-progress copy under review),
  otherwise `index.html`. Necessary because opening the file directly (double-click,
  no server) makes it fall back to fetching data from the live GitHub Pages site
  instead of your local files — this script is what lets you actually preview local
  changes, including data files, before they're pushed.

## Deployment

Live at **https://yashk-sse.github.io/Referral-Dashboard/** via GitHub Pages, from this
repo (`yashk-SSE/Referral-Dashboard`) — switched from Netlify due to its free-tier
monthly production-deploy cap. Pushing to `main` (whether from the Apps Script or
manually) triggers a redeploy.
