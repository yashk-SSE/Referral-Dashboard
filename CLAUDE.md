# SolarSquare Referral Dashboard — Project Context

> **Read this file in full before touching any code.** It contains business logic that is
> NOT obvious from the codebase and cannot be reverse-engineered from the data alone.
> `README.md` was a stale 1-line stub as of the first session (2026-08-03) and has since
> been rewritten to summarize this project properly. As of 2026-08-03, keeping both this
> file and `README.md` in sync with the actual code is a standing habit (see Section 12)
> — if a future session finds either one stale again, fix it as part of that session's
> work, don't just flag it and move on.

---

## 0. CURRENT STATUS — read this first, before anything else

**This section is a living snapshot, not history.** Keep it updated as work progresses —
when you finish a task or hand off, update this section before anything else in this file.
Detailed history lives in the numbered sections below and in `git log`; this is just
"what's true right now."

**As of 2026-08-04, end of session (updated — Phase 3 started, pending review):**

- **Customer App Phase 2 is LIVE in `index.html` and pushed to `origin/main`**
  (commit `7d1b610`) — the 4th channel switcher button, `capp` Overview tab, and
  `capptrend` MoM Trend tab, including the full round of review-feedback fixes (HOTO
  base bug via `hotoEffAt`, city multi-select filter on both tabs, shortened table
  headers, Absolute/%+login-month selector — see Section 15 for full detail). Yash
  reviewed and explicitly approved the merge and the push on 2026-08-04.
- **⚠️ `index.preview.html` exists again and is now AHEAD of `index.html`** — Phase 3
  work in progress, per Yash's own request this session. NOT yet reviewed/approved,
  do not merge/commit/push. What's in it but not in `index.html`:
  - Removed the "Logins on Base" standalone card from the `capp` Overview tab — Yash
    flagged it as redundant with the 3 fixed cards above it (picking HOTO/Installed/
    Commissioning in the dropdown just reproduced one of those 3 exactly). The
    `CAPPVEL_STAGE_CFG`-style 4-stage concept it introduced was **not** deleted, just
    relocated — see the new 3rd tab below, where it's load-bearing rather than redundant.
  - **New 3rd Customer App tab: `cappvel` → `bCAppVel()` — "Login Velocity"** (Phase 3).
    P50/P90/P95/Avg days from reaching a milestone (Order Booked/HOTO/Installation/
    Commissioning, picked via buttons) to a project's first login, for a custom
    date-range cohort (From/To inputs scoping which projects count, by when they
    reached that milestone — blank = lifetime). Own city multi-select filter
    (`cappvel-city`), India + per-city breakdown table. Full detail in Section 15.
  - Custom date-range cohort filtering (per the original Phase 3 ask) is now built.
    Still open for a future phase: nothing else was flagged as missing as of this
    snapshot — confirm with Yash before assuming Phase 3 is fully "done."
  - Browser-tested (city filter, stage buttons, date-range inputs incl. round-trip
    display, Reset button) — no console errors. **Not yet shown to Yash.**
- **Customer App data pipeline field fix is committed and pushed (2026-08-04):**
  `scripts/customer_app_query.sql` now sources HOTO from
  `project.sales_handover_datetime` and Installation from a `usertasks` task-`039A`
  completion timestamp, replacing `cx_approval_timestamp`/`project.installation_date`
  — per Yash's explicit instruction to match his own Metabase question 1466.
  `data/customer_app.json` re-pulled to match. Installation and Commissioning
  reconcile exactly against Yash's manually-read July'26 numbers (3,581 and 4,129).
  **HOTO does not fully reconcile** (pipeline: 3,949 for Jul'26 vs Yash's ~4,476
  manually-read figure) — **Yash's explicit call (2026-08-04): accept 3,949 for now
  and move on**, don't re-chase this without new info from him on where 4,476 comes
  from. **Scope note (make this explicit wherever this number is cited): 3,949 is
  `project_state IN ('active','completed')` only**, not an unfiltered count and not
  necessarily the same population as the main Referral dashboard's own HOTO actuals.
  Full detail in Section 15.
- **Everything else is committed and pushed** — confirm with `git fetch && git log
  --oneline origin/main..HEAD` (should be empty, aside from Phase 3 sitting unmerged
  in the gitignored preview file). Note the Apps Script also pushes automated
  `data/*.json` refresh commits straight to `main` throughout the day (commit messages
  like "📊 Referral leads: ...") — these are routine and don't touch `index.html`/
  `CLAUDE.md`; a local push getting rejected because of them just needs a
  `git pull --rebase origin main` before retrying, not a conflict investigation.
- **Two credential/data files exist locally, both gitignored, never committed:**
  - `.metabase_key/metabase_key.txt` — the Metabase API key. Read it only by having a
    script load it at runtime (see `scripts/pull_customer_app.py`) — never `Read` this
    file directly yourself, never print/echo its contents, never put it in a chat reply.
  - `Referral MOP Aug'26_Final.xlsx` (and Office's `~$...xlsx` lock file next to it) —
    this month's MOP source file, already consumed into `data/referral_mop.json`.
    Nothing further to do with it unless Yash provides a new one next month.
- **No hard-blocking open questions right now.** Section 13 has the standing list of
  soft/pending items (Stage Aging nav entry, Funnel MOP %, Customer_App reclassification
  not started, etc.) — none are blocking, they're just undecided/unscheduled.
- **Quick orientation for a fresh session:** read this file in full (as instructed above),
  then check `git log --oneline -15` for the recent narrative, then check whether
  `index.preview.html` exists before touching `index.html`. Section 15 has everything
  about the new Customer App/Metabase branch; Sections 1–14 cover the original
  Referral/Digital dashboard.

---

## 1. What this project is

A single-file HTML/JavaScript dashboard tracking the **Referral sales channel** funnel
performance for SolarSquare, a B2C solar company, across **32 Indian cities** (resolved,
see Section 6 for the exact list — no longer an open discrepancy).

- Deployed via **GitHub Pages** at `https://yashk-sse.github.io/Referral-Dashboard/`
  (not Netlify — corrected 2026-08-03; Netlify's free-tier monthly production-deploy
  limit was the reason for switching), sourced from this GitHub repo:
  `yashk-SSE/Referral-Dashboard`. No custom domain (no `CNAME` file) — default
  `github.io` URL.
- Data flow (confirmed from code, 2026-08-03): **BigQuery → Google Apps Script
  (`Referral Dashboard.gs`, v5) → JSON files pushed directly to this repo's `main` branch
  via the GitHub Git Data API** (uses a PAT stored in Apps Script Properties). This is the
  **sole authoritative pipeline.** There is no Google Sheets CSV anywhere in the current
  flow — `index.html` fetches `data/*.json` directly, nothing else.
- A second, independent pipeline (`scripts/fetch_data.py` run via
  `.github/workflows/update_data.yml` on a daily cron) used to write the *same* JSON files
  with an incompatible, simpler schema, racing the Apps Script. **Killed 2026-08-03** per
  Yash — both files deleted. Do not recreate without an explicit decision to migrate (see
  "Possible future direction" below).
- BigQuery source table: `presales-442917.leadcsv.Samagam` — confirmed, used by
  `Referral Dashboard.gs`.
- **Possible future direction for THIS (Referral) pipeline specifically (not scheduled,
  no timeline):** Yash may eventually move it back to Python/GitHub Actions. Still not
  happening — don't build toward this speculatively.
- **Metabase IS now connected (2026-08-03) — but for a separate, independent branch,
  not this pipeline.** See Section 15: a brand new "Customer App" branch sources from
  Metabase entirely independently of BigQuery/Apps Script. Don't confuse the two — the
  Referral/Digital pipeline above is untouched by this.
- **Digital channel is being gradually removed (2026-08-03, no timeline yet):** Yash's
  plan is to eventually drop the Digital-channel JSONs (`digital_effort.json`,
  `digital_leads.json`) and the Ref-vs-Digital compare view entirely, narrowing this
  dashboard back to Referral only (matching Section 1's original framing). Not urgent,
  no code changes made yet — don't touch the Digital channel code until told to.
- **Repo bloat from daily full-JSON commits — suggested long-term fix (not urgent,
  not implemented):** the Apps Script pushes full rewrites of `data/*.json` (tens of MB)
  to git on every run, so repo history grows every day forever. Removing the Digital
  JSONs helps some but `referral_effort.json`/`referral_leads.json` will keep growing.
  Git LFS doesn't really solve this — the files change daily so there's no dedup benefit.
  The clean long-term fix is to **stop storing this data in git at all**: have the Apps
  Script (or its Python/Actions successor) write the JSON to a small storage layer
  outside git — a Cloud Storage bucket, a lightweight API, or eventually just point
  Metabase straight at BigQuery — and have `index.html` fetch from that URL at runtime
  instead of from a git-tracked file. This is also the natural convergence point with
  the Metabase idea above: a real BI/serving layer removes the need for static
  JSON-in-git entirely. Flagging for whenever this becomes a real problem, not now.

### Known local files — confirmed by inspection (2026-08-03)

| Name | Type | Confirmed role |
|---|---|---|
| `.github/workflows/test.yml` | workflow | Trivial — `echo` on manual dispatch only. Not a real test/CI gate. |
| `.github/workflows/update_data.yml` | — | **Deleted** (was the killed Python pipeline's trigger). |
| `data/` | folder | 5 JSON files written by the Apps Script: `referral_effort.json`, `referral_leads.json`, `digital_effort.json`, `digital_leads.json`, `referral_mop.json`. First four are BigQuery-generated; `referral_mop.json` (MOP targets) is maintained separately/manually — not produced by any script in this repo. |
| `scripts/` | folder | **Emptied** — `fetch_data.py` deleted (killed pipeline). |
| `index.html` | 664 KB | The dashboard. 7,254 lines, single file, everything inline. Handles Referral **and** Digital channels plus a Ref-vs-Digital compare view (not Referral-only, despite Section 1's old framing). |
| `README.md` | — | Was outdated 1-line stub; now kept in sync with this file (see Section 12). |
| `Referral Dashboard.gs` | 32 KB | Apps Script v5. Queries BigQuery for **both** Referral and Digital (effort + lead-level), pushes each JSON straight to `main` via GitHub's API. This is the live, authoritative pipeline. **Was never committed to git before 2026-08-03** (existed only in the Apps Script editor / this local copy) — now tracked in the repo so the pipeline source has version history. |
| `referral-dashboard` | 1 byte, no extension | Confirmed: a single newline, no content, no function. Not a config or script. Yash's call (2026-08-03): leave it as-is, no action needed. |

**Note on Section 7 below:** the "Raw_Data_Effort" / "Raw_Lead_Data_updated" Google Sheets
tabs described there are **not used anywhere in the current pipeline** — no Google Sheets
fetch exists in `index.html` or either script. That section likely describes an earlier
architecture (or the original design behind the BigQuery query logic) that's since been
superseded by direct BigQuery → JSON. Column-level definitions in Section 7 still roughly
map to what the JSON files carry, but treat the "two Sheets tabs are the source of truth"
framing as stale until confirmed otherwise.

---

## 2. Business context — SolarSquare's sales channels

SolarSquare sells rooftop solar via six lead-generation channels:

1. **Digital**
2. **Referral** ← this dashboard's entire scope
3. **Solarpro** — channel partners, commission-based model
4. **BTL Activity**
5. **IVR**
6. **Others**

**Why Referral is prioritized:** most effective and economic channel, highest-intent
leads, highest conversion, and the channel that builds the most brand trust. It is meant
to be the top priority channel for every LRM and SC.

**FY27 target:** Referral channel is targeting **40,000 HOTOs** for FY27 (Apr 2026 –
Mar 2027). Every relevant view should show a running counter of YTD HOTOs achieved
against this 40,000 target, not just monthly MOP attainment.

---

## 3. The sales funnel

```
Lead → BQL → MS → MD → Order Booked → HOTO
```

| Stage | Meaning |
|---|---|
| **BQL** (Bill Qualified Lead) | Lead whose electricity bill has been qualified against threshold — ready to move forward |
| **MS** (Meeting Scheduled) | BQL for whom a physical meeting has been scheduled |
| **MD** (Meeting Done) | Scheduled meeting that has actually taken place at the customer's home |
| **Order Booked** | Customer has paid an advance amount after the meeting |
| **HOTO** (Handover-Takeover) | Final stage — Sales hands the customer over to Ops |

At each stage there are two outcomes (progress / no-progress), with the no-progress
side carrying various dispositions (Lost, Not Interested, Not Qualified, Not Connected,
Meeting Postponed, Meeting Rescheduled, Future Interest, Future Followup, Later
Interest, etc.). Orders can also be **cancelled after booking**.

**Known seasonality/lag:** there is always a gap between Order Booked and HOTO within
a given month, and both Order and HOTO trend very high in volume at month-end — treat
Order→HOTO timing as a structural lag, not an anomaly, when doing month-end analysis.

### Ownership handoff

- **LRM (Lead Relationship Manager)** owns the lead from BQL through **MD**. LRM does
  the first customer interaction and sets up the physical meeting (BQL→MS transition).
- **SC (Solar Consultant)** owns the lead from **MD onward** through Order and HOTO. SC
  conducts the physical home meeting.
- Reporting/ownership attribution for stage metrics: **LRM = BQL→MD, SC = MD→HOTO.**

---

## 4. Referral sub-channels (6 today — still 6 planned, attribution is changing, see flagged change below)

| Sub-channel | Source |
|---|---|
| **Sales** | Leads generated by the Sales team |
| **Online** | Leads generated organically via WhatsApp / online channels |
| **BTL** | Leads generated by BTL teams via on-ground activities |
| **Ops / AMC** | Leads generated by Ops/AMC ground staff |
| **Customer_App** | Leads generated directly by customers via the Customer App |
| **Referral_Others** | Other sources — HO team, self-employees, etc. |

**⚠️ Planned change (flagged 2026-08-03, corrected 2026-08-03, not yet implemented —
future work, don't build toward this until explicitly asked):** Per Yash, this is a
**reclassification, not a removal.** The *current* `Customer_App` sub-channel
attribution is wrong and that current logic will be removed — but a **new, correctly
attributed `Customer_App`** sub-channel will be added back, carved out of what's
today lumped into `Online` (`Online` is getting bifurcated, and one of the resulting
pieces is the real `Customer_App`). End state still has a `Customer_App` sub-channel
— it just comes from a different, corrected source classification. Do **not** treat
this as "delete all mentions of Customer_App" — that was my first (wrong) read of
this; the name survives, only its underlying attribution logic changes. Touches:
- `Referral Dashboard.gs` — the `Source_Sub_Class_final` CASE logic that currently
  maps `Source_Class LIKE '%Customer App%'` to `'Customer_App'` (this specific rule
  is the wrong one being replaced) and whatever rule currently produces `'Online'`
  (needs to split, with the correct Customer_App slice breaking out of it)
- `index.html` — the `SCS` constant and every sub-channel breakdown table/chart/filter
  that iterates it; `Customer_App` stays in the list, `Online` may need to become
  two entries depending on how the bifurcation is named
- `data/referral_effort.json` / `referral_leads.json` — sourced from BigQuery via the
  Apps Script, so this is fundamentally a **source-data reclassification**, not just a
  dashboard filter change — the BigQuery query logic itself needs the corrected split
  before anything downstream changes
- `referral_mop.json` if/when Sub-Channel MOP targets get built (Section 13)

Don't start this without explicit confirmation on: exact bifurcation of `Online`
(what the new sub-channel name(s) will be, and which existing rows move to the
corrected `Customer_App`), and whether historical `referral_effort.json`/
`referral_leads.json` rows need to be backfilled/relabeled or only new data goes
forward under the corrected attribution.

---

## 5. Terminology glossary (precision matters — these drive the calc logic)

| Term | Definition |
|---|---|
| **MOP** | Monthly Operating Plan — target set at month start, tracked vs actual MTD. Targets exist for BQL, MS, MD, Order, HOTO — at both **India** and **city** level. |
| **AOP** | Annual Operating Plan, broken down as a MoM plan. |
| **MoM** | Month-on-Month performance. |
| **WoW** | Week-on-Week performance. |
| **DoD** | Day-on-Day performance. |
| **M0 / Cohort view** | Same-month cohort: BQL generated in month X, and only the MS/MD/Order/HOTO that happened to **that same cohort of leads**, counted within month X. |
| **Effort** | BQL of month X, but MS/MD/Order/HOTO counts include **all actions taken in month X regardless of which month the underlying lead was created**. |
| **MTD view** | A day-X cutoff comparison across the last 5–6 months (i.e., performance of every month "as of the Xth"). Applies to both M0 and Effort views. |

### The four funnel-attribution variants (all four must exist as separate views)

1. **Effort Funnel** — BQL = current month. MS/MD/Order = **whole month**, any lead
   creation date. Compared over last 6 months (full-month vs full-month).
2. **Effort MTD Funnel** — same as above but MS/MD/Order truncated to **yesterday's
   date** of the current month; compared against the same day-cutoff in each of the
   last 6 months.
3. **M0 Funnel** — BQL = current month. MS/MD/Order = **whole month**, but **only for
   leads created in that same month** (cohort). Compared over last 6 months.
4. **M0 MTD Funnel** — same as M0 but truncated to **yesterday's date**; compared
   against the same day-cutoff in each of the last 6 months.

**Precision rule (from prior sessions — please reconfirm still accurate):** "Full
Month" = leads created 1st–last day with actions completing in that same full month;
for the *current, incomplete* month, Full Month collapses to MTD. MS→MD and MD→Order
cohort tables should only include leads whose *prior* stage also completed in the same
calendar month as creation.

**⚠️ Open ambiguity to confirm with Yash, not silently resolve:** the M0 MTD
description in this handoff also mentions comparing a day-X cut of the current month
against *both* a day-X cut **and** a full-month (through 30th/31st) figure for prior
months. It's unclear whether that's intentional (showing prior months' trajectory
alongside the same-day comparison) or a wording slip. Confirm before building/changing
any M0 MTD logic.

---

## 6. Cities & tiers

**RESOLVED (2026-08-03) — code is the source of truth.** The `TIERS` constant in
`index.html` is the real, current, 32-city list. It doesn't match either candidate list
that was previously in this file — it's effectively the union of both, plus Faridabad:

- **Focus (3):** Nagpur, Lucknow, Pune
- **Big (7):** Indore, Jabalpur, Chennai, Bhopal, Delhi, Nashik, Kanpur
- **Mid (9):** Gwalior, Aurangabad, Hyderabad, Bangalore, Amravati, Jaipur, Ahmedabad, Kolhapur, Varanasi
- **Small (4):** Gurgaon, Noida, Ghaziabad, Faridabad
- **Expansion (9):** Agra, Coimbatore, Jalgaon, Solapur, Meerut, Bareilly, Vijayawada, Kota, Ahilyanagar

**Known, expected gap — not a bug:** `referral_mop.json` (MOP targets) does not have
every city above. As of last check it's missing MOP targets for Meerut, Bareilly,
Vijayawada, Kota, and Ahilyanagar. Per Yash: this is expected — MOP is not created for
every Expansion city every month. `index.html`'s `hasMop(city)` already gates these out
of MOP-target tables correctly (only shows a city once `referral_mop.json` has a nonzero
entry for it) — no code change needed for this, just don't treat a missing MOP row as a
data bug.

**Known naming fix:** "Bengaluru" is remapped to "Bangalore" in `index.html` to match
MOP sheet keys — confirmed present and working (`cityFix()` / inline check on load).

**Sort convention:** Tier order first — Focus → Big → Mid → Small → Expansion — then
worst metric drop within tier.

---

## 7. Data sources — two Google Sheets tabs, used for different things

### `Raw_Data_Effort` (18 columns, date-wise action rows)
Source of truth for **MOP-vs-actual tracking** and the **Effort funnel** / MoM.

| Col | Field |
|---|---|
| A | Action date |
| B | Day |
| C | Month |
| D | Year |
| E | City (aka "Cluster") |
| F | Sub-Channel |
| K | BQL count on that date/city/sub-channel |
| O | MS count |
| P | MD count |
| Q | Order Booked count |
| R | HOTO count |

### `Raw_Lead_Data_updated` (lead-level, one row per lead)
Source of truth for **M0 cohort analysis, Stage Aging, and Velocity analysis**.

| Col | Field |
|---|---|
| A | Lead ID |
| B | City |
| D | Sub-Channel |
| I | SC App Stage (disposition) |
| L | Creation date |
| T | Meeting Scheduled timestamp |
| U | Meeting Done timestamp |
| V | Order Booked timestamp |
| W | HOTO Done timestamp |

### MOP numbers
Delivered as a **separate table** — targets for BQL, MS, MD, Order/HOTO at India and
city level. (Format to be confirmed on inspection — do not assume prior session's MOP
JSON schema still applies without checking.)

---

## 8. Critical calculation rules — do not deviate without asking

1. **Order now has its own explicit MOP target — do not proxy it off HOTO.**
   `referral_mop.json` carries a real `ORDER` field per city, and `index.html` compares
   actual Order MTD directly against `mFull.ORDER` (its own comment: *"Order — now uses
   its own explicit MOP target instead of the HOTO MOP as a proxy"*). HOTO MTD is
   compared against its own HOTO target, separately. **This supersedes the old
   HOTO-as-Order-proxy rule** — confirmed by Yash 2026-08-03, match what the code does.
2. **MD→Order% is the primary/standard lower-funnel metric.** MD→HOTO% is still shown
   throughout as a secondary reference figure (explicitly labeled "(ref)" in the Funnel
   Impact Analysis section) — it hasn't been removed, just demoted. Lead with MD→Order%
   in any new analysis; MD→HOTO% can appear alongside for context.
3. **Always show a running counter against the 40,000 HOTO FY27 target**, alongside
   whatever MOP/MTD view is on screen. Confirmed implemented (`FY_T = 40000`,
   `C.ytdHoto`, the `fy-mini`/`FY27 HOTO Tracker` UI).
4. Section 7's Google Sheets tabs are not part of the live pipeline (see Section 1) —
   in practice this rule now means: `data/referral_effort.json` → MOP comparisons +
   Effort funnel; `data/referral_leads.json` → M0, Stage Aging, Velocity. Same
   separation of concerns as before, just via JSON files instead of Sheets tabs.

---

## 9. Required report structure

- **Executive Summary** — 4–5 top-level callouts only, India-wide.
- **India Summary** — MOP vs MTD Actuals for BQL/MS/MD/Order/HOTO at India level, plus
  the FY27 40K-HOTO counter.
- **City Summary** — per-city MOP vs MTD actual, and vs LMTD (last month till date);
  tier-sorted per Section 6's convention; surplus/deficit flagged **red (>20% deficit)
  / green (surplus) only, no amber** (existing convention, confirm still wanted).
- **Sub-Channel Summary** — composition and performance by the 6 sub-channels, with
  city × sub-channel cross-tab.
- **Funnel Movement** — all 4 variants from Section 5 (Effort, Effort MTD, M0, M0 MTD),
  each covering BQL→MS, MS→MD, MD→Order, trended over last 6 months, city + sub-channel
  drill-down, with call-outs on which sub-channel/city is driving any drop.
- **Velocity** — P90/P75 days taken for BQL→MS, MS→MD, MD→Order, per city and
  sub-channel, trended over last 6 months.
- **Composition** — BQL/MS/MD/Order/HOTO composition by sub-channel, India and city
  level, trend direction, and a specific flag pattern: *sub-channel has high BQL
  composition but disproportionately low Order contribution* → indicates weak funnel
  movement for that sub-channel in that city.
- **Action Recommended** tab.
- **Insights** tab.
- **Filters** — at minimum: tier, city, sub-channel, month/date range, and (per
  existing dashboard) an Old/New BQL metric toggle.

### The analysis "story" this dashboard should tell

1. Start from current-month BQL/MS/MD/Order/HOTO vs MOP and vs LMTD.
2. Identify which cities are hitting target vs lagging target vs lagging even LMTD.
3. For lagging cities/metrics, drill to L2: which sub-channel is driving the gap, and
   is it an Effort-level or M0-level funnel movement problem?
4. If BQL is elevated somewhere — which city, which sub-channel?
5. If MD dropped — which city, which sub-channel, and is it a funnel-conversion issue
   or a volume issue?
6. If Orders are de-growing — which city is contributing the largest order loss, and
   which sub-channel within that city?
7. Every insight should be broken out at India → City → Sub-channel level.

---

## 10. Implementation details — CONFIRMED against code, 2026-08-03

Code is the final source of truth (Yash's standing instruction). Everything below has
been verified directly in `index.html` / `Referral Dashboard.gs`, not just recalled:

- Dashboard has 17 reachable Referral tabs (`REFERRAL_TABS` in `index.html`): `exec, mop,
  india, city, sc, funnel, m0funnel, bqlq, vel, wow, ins, act, dod, dodfunnel, cohort,
  citymom, citydeep` — plus a channel switcher (`Referral / Digital / Ref vs Digital`)
  that isn't itself a tab. `aging` (Stage Aging) exists in the code's internal `allTabs`
  list but is **not** in `REFERRAL_TABS` — see Section 13, it's built but unreachable.
- Helper functions `pN`, `f`, `getBQL()`, `getMS()`, `getMD()`, `METRIC_SEL` — **confirmed
  present and working exactly as described**: `METRIC_SEL = {bql, ms, md}` routes the
  Old/New BQL and First/Total MS/MD definitions everywhere via those three getters.
- `setMetricDef()` — **confirmed**: calls `precompute()` then clears `rendered = {}`
  then `sw(curTab)`, in that exact order.
- "Funnel Impact Analysis" with a "Cascade using" current/compared-month switcher —
  **confirmed present**, quantifies Order-unit impact of rate changes per stage.
- BQL Quality 6-segment cohort (Core/BQL_Old + 5 incremental groups) — **confirmed**,
  `BQL_SEGMENTS` constant matches exactly.
- Apps Script rolling-window/OOM-fix details (6-month window, `rows = null` after
  mapping) — not re-verified line-by-line this session; the `.gs` file's own v5
  changelog comment describes a different, more recent change (BQL_BASE widened to
  BQL_New definition, full-history backfill on every run since `pushToGitHub` overwrites
  wholesale) — treat that changelog comment at the top of `Referral Dashboard.gs` as the
  current authority on what the script does, not this bullet.
- **MOP Planner** and **Referral Lead Scoring** (`Campaign Cleaned × 0.423 + Pincode
  Density × 0.577`) — confirmed **not present in this repo** (no matches in
  `index.html`). Consistent with these being separate standalone tools, as previously
  understood. Still nothing to reconcile here.

---

## 11. Styling & formatting conventions (confirm still wanted, don't silently change)

- Minimal, professional grey/black styling — no colorful section headers.
- Surplus/deficit shown as simple **green/red only** — no amber.
- **1-decimal precision** on all percentages.
- Explicit "LMTD" comparison labels everywhere a comparison is shown.
- **pp (percentage point) deltas** shown inline, not as separate columns.
- **ASCII only** inside `<script>` blocks — non-ASCII characters (emoji, smart quotes,
  etc.) have previously caused silent JS syntax errors. Use string concatenation
  instead of deeply nested template literals if unsure.

---

## 12. How Yash wants to collaborate

- Direct, high-urgency communication style; all-caps sometimes used for emphasis or
  escalation — not a sign of frustration with you, just his style.
- **Strong preference: do not assume — ask when something is unclear.** Flag issues
  explicitly rather than silently resolving them. This file already models that
  (see the flagged discrepancy in Section 6, and the open ambiguity in Section 5).
- Prefers fast, working file output over long explanations.
- Will typically upload files directly rather than describing issues verbally, and
  share screenshots for visual bugs.
- **Standing instruction (2026-08-03): keep `README.md` and `CLAUDE.md` updated as a
  regular habit, proactively, whenever project context changes** — new decisions,
  resolved discrepancies, pipeline changes, schema changes, etc. Don't wait to be asked.
  Update these two files as part of finishing any task that changes what they describe,
  not just when explicitly told to.
- **Code is the final source of truth** for how the dashboard actually behaves — when
  code and docs disagree, fix the docs to match the code, don't silently trust either
  without checking, and say so when you make the correction.
- **Local-preview-before-push workflow (standing habit, 2026-08-03):** when making
  changes to `index.html` (or any other dashboard file), don't edit it in place. Instead
  edit a gitignored copy (`index.preview.html` — see `.gitignore`), leave the real,
  committed `index.html` untouched, and tell Yash to open the preview copy locally to
  review. Only after he approves: copy the preview over the real file, then
  `git add`/commit, and hold off on `git push` until he separately says go (per Section
  14/first-push precedent — pushing is still a distinct confirmation, reviewing the
  preview isn't the same as approving the push).
  **Important:** opening the file directly (double-click, `file://`) makes
  `fetchJSON()` fall back to fetching data from the live GitHub Pages site instead of
  local files — confirmed 2026-08-03 after this caused a real, confusing bug (stale
  MOP data with a missing field showing as 0 in a local review). `fetchJSON` now tries
  the local `data/` folder first and only falls back to production if that fetch
  throws, but Yash still needs to open the file through a local server for that local-first
  path to actually run — use `preview-local.bat` (double-click) for this, which starts
  a server on `http://localhost:8743` and opens `index.preview.html` (falling back to
  `index.html` if no preview copy exists).

---

## 13. Open / pending items

- ~~MOP data structure expansion: explicit Order stage~~ — **done.** `referral_mop.json`
  has an explicit `ORDER` field per city, consumed directly (Section 8, rule 1).
  **Still pending:** Funnel MOP (% targets) and Sub-Channel MOP (BQL/Order by
  Sales/Online/BTL at city level) — confirmed **not implemented** in `index.html` as of
  2026-08-03.
- Open question (still unresolved): should Funnel MOP target percentages be
  independently entered, or derived by formula from City MOP volumes? Ask before
  implementing either.
- **Stage Aging — precise current state confirmed 2026-08-03:** fully built, not
  reachable. `bAging()`, the `C.aging` computation (BQL→MS / MS→MD / MD→Order stuck-lead
  buckets), and a `<div id="p-aging">` panel all exist and render correctly. But no nav
  button anywhere calls `sw('aging', ...)` — `'aging'` is in the internal `allTabs` list
  but missing from `REFERRAL_TABS` (the list that actually drives the sidebar). **Pending
  decision from Yash:** add a nav entry to surface it, or is it deliberately hidden for
  now? Not touched yet.
- Lead scoring implementation format (how it plugs into the main dashboard) —
  undecided, and the tool itself isn't in this repo (see Section 10).
- **Reclassify `Customer_App` sub-channel** — current attribution is wrong and gets
  replaced with a corrected `Customer_App` carved out of `Online`'s bifurcation
  (not a removal — the name stays). Flagged 2026-08-03, future work, not started.
  Full detail in Section 4. Touches the Apps Script's BigQuery source-data
  classification, not just the dashboard.
- Possible future pipeline migration to Python/GitHub Actions + Metabase — see
  Section 1. Not scheduled, no timeline, don't build toward it yet.
- `Referral MOP Aug'26_Final.xlsx` appeared in the local working folder mid-session
  (2026-08-03), not yet explained by Yash. `.gitignore`'d for now, not pushed, not read.
  Likely this month's MOP source file — ask before doing anything with it.

---

## 14. First-session checklist for Claude Code

Do this **before** making any code changes:

1. Confirm this folder is a real `git` clone of `yashk-SSE/Referral-Dashboard` (not a
   manual copy) — run `git status` / `git remote -v`.
2. Open and actually read: `index` (likely `index.html`), `Referral Dashboard.gs`,
   everything in `scripts/` and `data/`, and whatever `referral-dashboard` (no
   extension) turns out to be. Report what each one actually does.
3. Explicitly disregard `README.md` as a source of truth — but flag anything in it
   that's worth salvaging or that contradicts this file.
4. Cross-check Section 6 (city/tier list), Section 10 (implementation details), and
   Section 13 (open items) against what you actually find in the code. Report
   discrepancies — don't silently trust either source.
5. Do not make changes yet. Summarize current state first and wait for direction.

---

## 15. Customer App branch — new, in progress (started 2026-08-03)

A completely new, separate branch of this dashboard, tracking Customer App logins
against 5 lifecycle milestones. Not a Referral-channel feature — its own switcher
alongside Referral / Digital / Ref vs Digital (not yet added to the UI as of this
writing — see status below). Sourced from **Metabase**, not BigQuery — an entirely
independent pipeline from everything else in this file.

### Data source
- Metabase instance: `https://metabase-lighthouse.solarsquare.in/`, database id `2`
  ("SolarSquare", Postgres). Read-only API key access — **no write/create permission
  in Metabase**; any new saved Question must be guided for Yash to create himself,
  never created by Claude directly.
- API key lives in `.metabase_key/metabase_key.txt` (gitignored, never committed,
  never printed/read directly into a chat transcript — scripts read it from disk at
  runtime only).
- **Metabase's `/api/dataset` silently caps results at ~2,000 rows** even for a plain
  unaggregated `SELECT` — confirmed 2026-08 (a 116,666-row query came back as exactly
  2,000 with no error). Fix: pass `"constraints": {"max-results": 1000000,
  "max-results-bare-rows": 1000000}` in the query payload. Already baked into
  `scripts/pull_customer_app.py` — don't drop this if the script is ever rewritten.

### Business logic (confirmed with Yash, 2026-08)
- **Login definition:** `otps` table, `"isVerified" = 'True'` AND `source IN
  ('CONSUMER', 'CUSTOMER_JOURNEY_TRACKER')`. **Not** `consumer_analytics` /
  `capp_login_successful` (an earlier, wrong guess — that table tracks Customer App
  UI events generally, but Yash's own established query uses `otps`).
- **Attribution chain:** `otps.mobile → customer.phone → customer.projects →
  customer_projects (index_=0) → projects_sseid → project.sseid`.
- **Milestone dates + city (current, as of the 2026-08-04 field correction below):**
  - Order Booked = `project.order_closure_datetime`
  - HOTO = `project.sales_handover_datetime` (changed 2026-08-04, was
    `project.cx_approval_timestamp` — see the correction note right below)
  - Installation = `usertasks` task-`039A` completion timestamp (changed
    2026-08-04, was `project.installation_date` — see below)
  - Commissioning = `project.commissioning_date` (unchanged)
  - City = `project.site_address_cluster`
  - Lead ID = `project.lead_id` (directly on `project` — no `lead` join needed at all
    for this feature)
- **HOTO and Installation field sources corrected 2026-08-04, per Yash's explicit
  instruction to match his own Metabase question 1466 ("OMS Plants").** A
  numbers-don't-match-up check against card 1466 and card 1182 ("CApp Login Report")
  surfaced that those two reference questions use different underlying columns than
  this pipeline did at the time — Yash's call was to **switch this pipeline to match
  card 1466**, not the other way round:
  - **HOTO is now `p.sales_handover_datetime`** (card 1466's "Sales Handover Date"),
    replacing the earlier `p.cx_approval_timestamp`.
  - **Installation is now the `usertasks` task-`039A` completion timestamp** (card
    1466's "Installation Completion Date"), replacing the earlier
    `p.installation_date`. Pulled via a new `install_task` CTE in
    `scripts/customer_app_query.sql`, joined on `project._id` (not `sseid` —
    `usertasks` has no direct sseid column). Kept as a full timestamp rather than
    card 1466's `::date`-truncated display value, so day-level velocity calcs keep
    hour-of-day precision.
  - Commissioning is unchanged (`p.commissioning_date` already matched card 1466).
  - Login source stays `IN ('CONSUMER', 'CUSTOMER_JOURNEY_TRACKER')` — Yash confirmed
    keeping `CUSTOMER_JOURNEY_TRACKER` even though card 1182 only filters `CONSUMER`.
  - **Verified after re-pulling `data/customer_app.json` (2026-08-04):** using a
    same-month (Jul'26) cohort-size reconciliation against Yash's own manually-read
    numbers — Installation now matches **exactly** (3,581 = 3,581, previously 3,533)
    and Commissioning still matches exactly (4,129 = 4,129, unchanged). **HOTO does
    NOT fully reconcile** even after the field switch (pipeline shows 3,949 for
    Jul'26 vs Yash's ~4,476 manually-read figure) — flagged back to Yash 2026-08-04.
    **Yash's call (2026-08-04): accept 3,949 and move on for now** — don't re-chase
    this gap without new information from him on where the 4,476 figure comes from.
    **Explicitly note the scope this 3,949 (and all Customer App HOTO/Install/Comm
    figures) represents: `project_state IN ('active','completed')` only** — this is
    not a full/unfiltered count of all HOTOs in July, and not necessarily the same
    population as the main Referral dashboard's own (Referral-channel-only) HOTO
    actuals. Don't assume the HOTO field is "fully correct" just because
    Installation/Commissioning reconciled — this specific number is accepted as a
    working figure, not a fully confirmed one.
- **Only the FIRST login per project is tracked, not every login — corrected
  2026-08-03.** The initial build tracked every login event; Yash confirmed only the
  first one matters for this feature. This also surfaced a bigger issue: the original
  query started from `otps` (INNER JOIN to `project`), which silently excluded every
  project with **zero** logins entirely. That's wrong for the "% of base logged in"
  stats below, which need the full project universe as the denominator. The query is
  now anchored on `project` (`LEFT JOIN` to a `MIN(created_at)`-per-sseid login CTE),
  so every project appears, with `first_login_at = NULL` for those with no login yet.
- **5 milestone windows** (per the original request): Before Order Booked · Order
  Booked→HOTO · HOTO→Installation · Installation→Commissioning · After Commissioning.
  Bucketing a project's *first* login into a window, and (eventually, Phase 3)
  computing days-elapsed-since-window-start, is done **client-side in the dashboard's
  JavaScript** — deliberately not pre-aggregated in SQL — because "custom date range
  cohort" filtering (per the original ask) needs raw per-project data to re-slice on
  the fly, the same reason the existing Velocity tab computes P75/P90 client-side
  rather than in a query. Projects with no login at all don't get a milestone bucket
  at all — they're tracked separately via the "% of base logged in" stats, not forced
  into one of the 5 windows.
- **`date_anomaly` flag:** `TRUE` when `commissioning_date < installation_date` for a
  project — confirmed by Yash as a rare, genuine data anomaly (not normal sequencing).
  Rows are **not dropped**. They're excluded from the City × Milestone bucketing table
  specifically (their install/commission sequence can't be trusted to place a login in
  the right window) but **are still counted** in the "% of base logged in" stats — the
  anomaly is about stage *ordering*, not about whether the project/login is real.
  Observed rate: ~2.0% of projects (1,160 / 58,313 after the `project_state` filter
  below) — if this rate ever climbs much higher, that's worth a second look, not just
  filtering. **UI note (2026-08-03):** don't surface this anomaly count at the top of
  the tab — a prominent red banner up front reads as "the data is wrong." It's now a
  small muted note near the bottom instead, alongside the Phase-2-scope note.
- **`project_state` filter, added 2026-08-03:** only `'active'` and `'completed'`
  projects are included (lowercase, confirmed against the actual data) — excludes
  `'cancelled'`, `'on-hold'`, `'seeking-cancellation'`, and null-state rows. Per Yash.
  Dropped the total base from ~73,600 to ~58,300 projects.
- **No red/green coloring on the "% of base logged in" cards, added 2026-08-03:** per
  Yash, 50% isn't a meaningful benchmark for this yet. Don't reintroduce a color
  threshold here without asking first — unlike the rest of the dashboard (95% vs MOP,
  etc.) this metric doesn't have an established target.
- **`capp_logged_in` boolean** (directly on `project`) can be used as a sanity-check
  cross-reference (e.g. does its count roughly match distinct logged-in SSEIDs) but
  **cannot** drive milestone bucketing — it has no timestamp.
- **City merge map** (confirmed 2026-08, applied in the puller script's
  `CITY_MERGE_MAP`): `Bengaluru→Bangalore` (same rename already used for Referral
  data), `Ajmer→Jaipur`, `Baroda→Ahmedabad`, `Mysuru→Bangalore`, `Salem→Bangalore`.
  **Not merged, kept as their own distinct cities:** `Raipur` (new city, expected to
  be added to the Referral dashboard's own tier list next month) and `Surat`
  (discontinued city, kept separate/inactive rather than folded elsewhere).
  Rows with no real city (true SQL NULL, or the literal 4-character string `"None"`
  found in at least one source row — a genuine source-data quirk, not a NULL) are
  **dropped entirely**, not shown as a fake blank-city bucket.
- **`Ghaziabad`/`Faridabad`/`Ahilyanagar` — resolved 2026-08:** none of the three
  appear anywhere in `project` under those exact names or any close variant checked
  (`%ahmed%`, `%ahilya%`, `%ghaz%`, `%farid%`, `%delhi%`, `%ncr%` all came back empty).
  Per Yash: `Ghaziabad→Noida` and `Faridabad→Gurgaon` are added to `CITY_MERGE_MAP` as
  forward-looking/defensive mappings in case either ever shows up in a future pull
  (neither does as of the 2026-08-03 data). `Ahilyanagar` gets no mapping at all —
  intentionally left out for now, not a bug if it stays absent.

### Pipeline status
- `scripts/customer_app_query.sql` — the finalized query, **rewritten 2026-08-03**:
  one row per **project** (anchored on `project`, not `otps`), with `first_login_at`
  (via a `MIN(created_at)` CTE, `NULL` if no login) + that project's milestone dates +
  city + `date_anomaly`. This is the **single source of truth**, also meant to be
  pasted into a standalone Metabase SQL question for Yash's own independent use —
  keep both in sync if this ever changes.
- `scripts/pull_customer_app.py` — the puller script. Reads the API key from
  `.metabase_key/`, runs the query above via Metabase's API (with the row-cap fix),
  applies the city merge + null-city drop, writes `data/customer_app.json`.
  Run manually for now (`python3 scripts/pull_customer_app.py`) — not yet automated
  via any scheduled job; that's a separate future decision, not assumed.
- `data/customer_app.json` — ~58,300 rows as of 2026-08-03 (one per active/completed
  project, not per login — row count moves slightly between pulls, live production
  data), ~15.9 MB. Contains real customer-level data (`sseid`, `lead_id`, login
  timestamp) — consistent with the existing `referral_leads.json` already doing the
  same in this public repo, not a new category of exposure.
- **Phase 2 (2026-08-03, first round of Yash's review feedback addressed —
  built in `index.preview.html`, not yet merged to `index.html`, not yet
  re-reviewed/approved):** a 4th channel switcher button ("Customer App",
  `ACTIVE_CH='capp'`) alongside Referral/Digital/Ref vs Digital, its own sidebar
  section (`data-ch="capp"`, same show/hide mechanism as Digital's `data-ch="digital"`
  items), and **two tabs**:

  **`capp` → `bCApp()` — Overview:**
  - A city multi-select filter (`capp-city` widget, `CAPP_ALL_CITIES` as the option
    list so non-`TIERS` cities like Raipur/Surat are selectable too) scopes
    everything below it — stat cards and the City × Milestone table (including its
    India row, which becomes the sum over just the selected cities). Same
    `insertMSWidget`/`buildMultiSelect` widget already used elsewhere in the
    dashboard (e.g. India Summary's tier/city/sub-channel filters).
  - Three top-line cards (no color coding, see above): % of Commissioned/Installed/
    HOTO base that has ever logged in (each base counted independently — a
    commissioned project is also installed and HOTO'd, not mutually exclusive groups).
    **HOTO base bug fix (2026-08-03, per Yash's review):** some projects have no
    `hoto_at` recorded but DO have a real `installation_date`/`commissioning_date` —
    since Installation/Commissioning can't happen without HOTO already having
    occurred, these now count as HOTO'ed via a new `hotoEffAt` fallback field
    (`hotoAt || instAt || commAt`), used everywhere HOTO base/bucketing logic runs.
    This also fixed a real bucketing bug: ~1,284 first-logins nationally were being
    dumped into "Order Booked→HOTO" purely because `hoto_at` was blank, when in
    reality they'd logged in much later (mostly "After Commissioning") — confirmed
    by the before/after city-level numbers matching exactly on reconciliation.
  - ~~A standalone "Logins on Base" dropdown card~~ was added then **removed
    2026-08-04** — Yash flagged it as redundant with the 3 fixed cards above (picking
    HOTO/Installed/Commissioning in its dropdown just reproduced one of those 3
    exactly). The underlying 4-stage concept (Order Booked/HOTO/Installation/
    Commissioning) wasn't wasted — it's now `CAPPVEL_STAGE_CFG`, load-bearing in the
    new `cappvel` Login Velocity tab below, where it isn't redundant with anything.
  - A City × Milestone table classifying each project's *first* login into one of the
    5 windows, tier-sorted, India total row, PLUS 3 more columns per city/India:
    % of that city's own Total HOTOs/Installations/Commissionings that have logged in
    (same stat as the top cards, just computed per-city instead of India-wide —
    `CAC.cityBaseStats[city]`). Only projects with a login and without `date_anomaly`
    appear in the 5 milestone columns (see the `date_anomaly` note above) — the 3
    %-of-total columns are independent of that, always lifetime (unaffected by the
    month selector below), and use the full per-city base.
    - Column headers shortened to fit on one line (e.g. "Order→HOTO",
      "HOTO→Install") with the full milestone name as a hover tooltip
      (`CAPP_MILESTONE_SHORT`) — fixes header/sort-icon wrap clutter Yash flagged.
    - **Absolute/% toggle** (`setCAppTableMode`) — "%" mode shows each of the 5
      milestone cells as row-composition %, i.e. % of that row's (city's or India's)
      own total, not a share of any city/column total. Lets you read the
      distribution shape per city at a glance.
    - **Login-month selector** (`setCAppTableMonth`, trailing 12 months via
      `capGetMonths()`) — restricts the 5 milestone columns + Total to first-logins
      that happened in the selected month only, so flipping through months shows
      whether a given stage (e.g. "HOTO→Install") is trending up or down. The 3
      "% of Total X" columns intentionally do NOT respond to this — they're a
      lifetime cohort stat (% of a city's full HOTO/Install/Comm base that has ever
      logged in), a different question from "logins that happened in month X," so
      mixing the two would be misleading.
    - Both controls recompute from `CAC.bucketable`/`CAC.cities` (stored on `CAC` by
      `precomputeCApp()`) via `capMilestoneTable(monthFilter)` — they don't re-run
      `precomputeCApp()`, so the always-lifetime stat cards above are never affected
      by them, only by the city filter.
  - The anomaly-count note near the bottom, deliberately not at the top (per Yash).

  **`capptrend` → `bCAppTrend()` — MoM Trend:**
  - Same city multi-select filter as the Overview tab (separate widget instance,
    `capptrend-city`, its own independent selection state).
  - A base selector (HOTO / Installed / Commissioned) driving a trailing-12-month line
    chart + data table: cumulative base size reaching that milestone by each month,
    and the login rate against that cumulative base shown **two ways** (per Yash,
    2026-08 — build both rather than pick one, resolving the earlier open question):
    - **% by month end** — of everyone reaching this milestone by month M, how many
      had logged in by M's own close (a freshness/decay view).
    - **% by now** — of that same cumulative base, how many have logged in as of
      today (the data-pull time).
    In practice these visibly converge for older cohorts (they've had more time to
    log in since their month closed) and stay close together for recent cohorts —
    confirmed this shows clearly in the first real chart, 2026-08-03. The HOTO series
    here uses the same `hotoEffAt` fallback as the Overview tab.
    `precomputeCApp()`'s `momTrend()` computes this per base into `CAC.momTrend`.

  `precomputeCApp(cityFilter)` / `capMilestone()` do the actual bucketing — a
  project's first login falls into the first milestone window it hadn't passed yet
  as of that login (checked against `hotoEffAt` for the HOTO boundary, not raw
  `hotoAt`); a missing (null) milestone date is treated as "not reached yet," not
  skipped over. Cities not in the Referral dashboard's own `TIERS` list (`Raipur`,
  `Surat`) render with no tier tag, sorted after all known tiers (`capTierSort()`).
  `CAPP`/`CAC`/`CAPP_ALL_CITIES` are the new global arrays (raw rows / precomputed
  aggregates / master city list for the filter widgets), following the same `ED`/`C`
  and `DED`/`DC` naming convention already used for Referral and Digital.

- **Phase 3 (2026-08-04, started per Yash's request — built in `index.preview.html`,
  not yet merged to `index.html`, not yet reviewed):** a 3rd tab.

  **`cappvel` → `bCAppVel()` — Login Velocity:**
  - Answers the original Phase 3 ask: P50/P90/P95/Avg days between a project
    reaching a milestone and its first login, for a **custom date-range cohort** —
    not just the fixed trailing-12-month windows the other two tabs use.
  - Own city multi-select filter (`cappvel-city`, same widget/pattern as the other
    two tabs, independent selection state) plus a stage picker
    (`CAPPVEL_STAGE_CFG`: Order Booked/HOTO/Installation/Commissioning — the same
    4-stage concept that used to be the removed "Logins on Base" card) and two
    `<input type="date">` From/To fields (`setCAppVelFrom`/`setCAppVelTo`, a "Reset
    (lifetime)" button clears both). Blank = unbounded on that side.
  - **Cohort definition:** projects whose *chosen stage's own date* falls in
    [From, To] (inclusive; blank side = no bound). This is deliberately about *when
    the project reached the stage*, not when it logged in — lets you ask "of
    everyone who hit HOTO in Q2, how fast did they log in?" rather than slicing by
    login date.
  - **Days-since calc:** only logins at/after the chosen stage's date count toward
    the P50/P90/P95/Avg (`capVelocityStats()`, using the shared `dD()`/`perc()`
    helpers already used by the main Referral dashboard's own Velocity tab). A login
    that happened *before* the chosen stage is excluded here, not treated as a data
    error — it belongs to an earlier milestone window (consistent with the
    half-open-interval boundary rule confirmed with Yash: the stage's own instant
    counts as the start of the window *after* it, never the one before).
  - **Two login-rate stats shown side by side, added 2026-08-04 per Yash's review**
    (both stat cards and both table columns): **% Ever Logged In** (total login
    rate for the cohort regardless of timing — includes logins that happened
    *before* the chosen stage) alongside **% Logged In (at/after)** (the subset
    whose login happened at/after the stage, which is the only subset feeding the
    days-since percentiles). Showing only the at/after figure understated the
    cohort's real login rate, since some projects log in earlier than the stage
    being measured — both numbers are needed for clarity, not a replacement of
    one by the other.
  - India + per-city breakdown table, tier-sorted, same structure as the Overview
    tab's City × Milestone table. Percentiles are computed from each row's own
    pooled day-array (not averaged from other rows), same as the main dashboard's
    Velocity tab convention.
  - **"Active/Completed projects only" caveat added to all 3 Customer App tab
    subtitles, 2026-08-04 per Yash's review** — not just documented in CLAUDE.md,
    now visible in the dashboard itself (`capp`, `capptrend`, and `cappvel` psub
    lines all state it) since every Customer App figure is scoped to
    `project_state IN ('active','completed')`, and that scope wasn't previously
    visible to anyone just looking at the tab.
  - Local-date input round-trip fix: the From/To `<input type="date">` values are
    formatted back for display using local `getFullYear/getMonth/getDate`, not
    `toISOString()` — the latter (used elsewhere in the codebase for similar date
    inputs, e.g. City Deep Dive) shifts the displayed date back a day in +IST for
    an input constructed at local midnight. Worth revisiting those other call sites
    if this ever surfaces as a real bug there, but out of scope to touch unprompted.
  - Browser-tested: city filter, stage switch, custom date-range (cohort correctly
    narrows, e.g. full-lifetime Commissioned base 51,212 → 16,060 for a Jan–Jun 2026
    window), Reset button, round-trip date-input display — no console errors.
- **Not yet built:** nothing else was explicitly flagged as in-scope for Phase 3 as
  of this snapshot — confirm with Yash before assuming it's fully "done" rather than
  just "the two things he asked for are built."
