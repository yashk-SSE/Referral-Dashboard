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

**As of 2026-08-25 (updated — found + fixed a real Customer App data-pipeline
regression that had been silently live for about a week, pushed):**

- **⚠️ The Customer App pipeline had been silently pulling only 2,000 of
  ~60,244 projects since around 2026-08-18 13:24 UTC — roughly a week of
  every Customer App number being wrong** before Yash caught it by noticing
  the Login Velocity tab showing ~226 lifetime installs pan-India (expected
  ~7,296 for a 2-month cohort). Root cause: Metabase stopped honoring the
  `"constraints": {"max-results": ...}` override in the `/api/dataset` JSON
  endpoint payload (confirmed 2026-08-25 via a live diagnostic query — the
  response's own `json_query.constraints` came back `None` even though we
  sent it, i.e. Metabase/the API gateway now drops the field rather than just
  ignoring its value) — so every pull since 08-18 13:24 UTC silently reverted
  to the ~2,000-row display cap, with **no error, timeout, or other signal**
  that anything was wrong. Nothing in this repo changed to cause it —
  confirmed via `git log` on `scripts/pull_customer_app.py`/
  `customer_app_query.sql` (no edits since 2026-08-05) and by diffing row
  counts across the auto-pull commit history (59,367 rows on the 08-18 09:59
  UTC pull → exactly 2,000 on every pull since, for a full week). This is a
  **Metabase-side behavior change**, not a query/schema change — a live
  `COUNT(*)` against `project WHERE project_state IN ('active','completed')`
  confirmed the true population is 60,244.
- **Fix (in `scripts/pull_customer_app.py`, `run_metabase_query()`): switched
  from the JSON `/api/dataset` endpoint to the CSV export endpoint
  (`/api/dataset/csv`)** — confirmed this returns the full, uncapped result
  set with no constraints override needed (this is the same endpoint
  Metabase's own UI "Download results" button uses, so it's an
  intentionally-uncapped path, not a workaround likely to get patched away).
  Two small follow-on normalizations were needed since CSV round-trips values
  differently than the old JSON response did: `date_anomaly` comes back as
  the string `"true"`/`"false"` (normalized to a real bool), and NULL
  timestamp fields come back as `""` rather than absent/`null` (normalized to
  `None` for the 5 date fields before writing JSON) — both purely
  representational, no logic changes. **If this ever regresses again**, the
  script's own comment on `run_metabase_query()` has the exact 4-query
  diagnostic to re-run (bare `COUNT(*)`, bare `SELECT` via `/api/dataset`,
  bare `SELECT` via `/api/dataset/csv`) before assuming anything else changed.
- **Re-pulled with the fix, verified, committed and pushed**
  (`data/customer_app.json` now 60,234 rows / 34 cities after the null-city
  drop + merge map — up from the broken 2,000). Re-checked the exact cohort
  Yash flagged (Installation reached in Jun 1–Jul 31 2026): **7,282 in the
  fixed data vs Yash's own reported ~7,296** — matches closely, confirms the
  fix. The GitHub Actions scheduled pull (`pull_customer_app.yml`) needed no
  changes itself — it just runs this script, so it picks up the fix
  automatically on its next scheduled run.
- **Every Customer App number pulled between 2026-08-18 13:24 UTC and this fix
  landing (2026-08-25) was silently wrong (undercounted, ~97% of projects
  missing)** — if Yash pulled any figures from the Customer App tabs during
  that ~week-long window for reporting, they should be re-checked against the
  now-fixed data.

**As of 2026-08-19 (updated — new "Actuals vs MOP" tab + City Summary/sort/freeze
polish, LIVE and pushed):**

- **New `avm` "Actuals vs MOP" tab is LIVE in `index.html`/`origin/main`**
  (commit `7fd723b`, reviewed and pushed same session). Sits right under "MOP vs
  MTD" in the sidebar. India row + all 27 cities with an Aug'26 MOP target,
  tier-sorted, grouped columns: **MOP Targets** / Actuals / Deficit / **Order
  Loss Attribution** / Projections (group header labels exactly as named —
  Yash asked for these specific wordings over the tab's original draft
  "Target"/"Loss Attribution"). Decomposes the MTD Order deficit into 3
  effects using a sequential-substitution bridge, built off **MOP's own
  BQL→MD and MD→Order implied rates — deliberately NOT the dashboard's usual
  3-stage BQL→MS→MD→Order funnel**, per Yash's explicit spec:
  1. **BQL Volume effect** — `(actualBQL - mtdTargetBQL) * targetR1 * targetR2`
  2. **BQL→MD Conversion effect** — `actualBQL * (actualR1 - targetR1) * targetR2`
  3. **MD→Order Conversion effect** — `actualBQL * actualR1 * (actualR2 - targetR2)`

  where R1 = MD/BQL rate, R2 = Order/MD rate, target = full-month MOP figures
  (ratio-invariant to prorating), actual = MTD. Sum of the 3 effects reconciles
  exactly to the MTD Order deficit (verified). The tab reads off the *existing*
  `ED`/`MOP` globals, so **no new BTL switch was built** — flipping the
  top-bar BTL include/exclude toggle already recomputes this tab live, same as
  every other Referral tab. `avm` is intentionally **not** in `REFERRAL_TABS`
  (so it's skipped by Timeframe/6-month mode entirely, same precedent as the
  unreached `aging` tab) — MOP tracking is inherently a current-month concept.
- **City Summary changes, same commit:** added a **BQL→MD%** column; both
  **BQL→MD%** and **MD→Ord%** now show Actual / MOP Target / LMTD together
  (colored green/red vs the MOP target rate specifically) — the other funnel
  columns (BQL→MS%, MS→MD%, MD→HOTO%, BQL→Ord%) deliberately stay LMTD-only,
  per Yash's explicit instruction that MOP-rate comparison is only meaningful
  for BQL→MD and MD→Order. **BQL→HOTO% column removed** entirely (5 render
  sites updated: `bCity()`'s India + city rows, `filterCityTable()`'s filtered
  aggregate + plain-India + per-city rows).
- **Frozen header row(s) + City column**, same commit, on all 3 wide tables —
  City Summary, MOP vs MTD, and the new Actuals vs MOP — via a new `.tw.freeze`
  CSS class (own internal `max-height`/`overflow:auto` scroll box, independent
  of the page's own sticky top bar, so no offset math against that bar was
  needed). Two-row grouped headers get per-row `top` offsets tuned against
  actual measured render heights (28px generically, 27px override for City
  Summary's slightly shorter row — see `#city-perf-tw` CSS rule); re-measure
  and adjust if header font-size/padding ever changes.
- **⚠️ Found and fixed a real pre-existing bug in the shared `makeSortable()`
  sort utility** (used by ~15+ tables dashboard-wide via `autoSort()`), while
  wiring up column-sort for the 3 tables above: it indexed columns via a flat
  count across *every* `<thead th>` (all header rows concatenated), which only
  happens to line up with tbody `<td>` indices for a single-row header. Any
  table with a grouped 2-row header (rowspan corner/spacer cells + colspan
  group titles — exactly City Summary/MOP vs MTD/Actuals vs MOP's own layout)
  was **silently sorting the wrong column** — e.g. clicking "MTD Order
  Deficit" was actually sorting by "Loss by MD→Order Deficit". Rewrote it to
  simulate the real header grid (`computeHeaderGrid()`, rowspan/colspan-aware)
  so only the last header row's cells are clickable and each maps to its true
  table-column index. Verified this didn't regress any pre-existing
  single-row-header table elsewhere (BQL Quality, Sub-Channel, etc. all
  re-tested after the change). India/aggregate rows stay pinned at the top of
  every sort (fixed a related edge case: City Summary's India row wasn't
  matching the old exact-match `'India'` pin check because its markup
  concatenates a tier-badge span's text into the same cell — pin check is now
  `startsWith('India')`).
- A one-off Excel report (`Referral_MOP_Report_Aug26_v2.xlsx`, not tracked in
  the repo) was also built this session with the same India+City MOP-vs-MTD
  and Order-loss-bridge analysis, both with and without BTL, for Yash's own
  offline use — mentioned here only for context, nothing in the repo depends
  on it.

**As of 2026-08-05, end of session (updated — 4th Customer App tab built, pending review):**

- **Customer App is fully LIVE in `index.html`/`origin/main`** through: Phase 2
  (`capp` Overview, `capptrend` MoM Trend — commit `7d1b610`), Phase 3 (`cappvel`
  Login Velocity — commit `e651ef4`), the HOTO/Installation field fix (commit
  `da50a1f`, see below), and a top-bar polish round — "last updated" timestamps
  (`#data-updated-lbl`/`#capp-updated-lbl`, mutually exclusive by channel, "IST"
  suffix dropped), a dashboard-wide table row-hover highlight, and the 8-button
  metric-switcher group collapsed into a single "⚙ Metrics" dropdown (channel
  switcher deliberately left as tabs — only 4 options, switched often) — commit
  `410899b`. Yash reviewed and explicitly approved every round before it was
  merged/pushed. Full detail in Section 15.
- **Customer App HOTO/Order Booked field sourcing — reversed AGAIN 2026-08-05,
  NOT YET committed/pushed (applied locally; ready to push whenever asked — Yash
  has confirmed keeping both fields on the `lead` table, see below).** History,
  in order (don't re-litigate earlier steps without new evidence):
  1. Originally: HOTO = `project.cx_approval_timestamp`, Order Booked =
     `project.order_closure_datetime`, Installation = `project.installation_date`.
  2. 2026-08-04: HOTO → `project.sales_handover_datetime`, Installation → a
     `usertasks` task-`039A` completion timestamp — per Yash's instruction to
     match his own Metabase question 1466. Installation and Commissioning
     reconciled exactly against his manually-read July'26 numbers (3,581, 4,129).
     HOTO did not (3,949 vs his ~4,476) — accepted as a working figure at the time.
  3. **2026-08-05 (current): HOTO → `lead.cx_approval_timestamp`, Order Booked →
     `lead.order_closure_datetime`** — per Yash's explicit instruction, backed by
     his own `COUNT(*)` reference queries against `public.lead` (226 HOTO, 442
     Order Booked, both for `>= '2026-08-01' AND < '2026-08-06'`). Note this is
     the SAME field name for HOTO as step 1 (`cx_approval_timestamp`) but now off
     the **`lead`** table, not `project` — genuinely different data, not a revert.
     Installation stays the task-`039A` timestamp from step 2; Commissioning
     (`project.commissioning_date`) has never changed. Joined via
     `project.lead_id = lead.lead_id` (LEFT JOIN — not every project resolves to
     a lead row).
  - **Reconciliation after re-pulling `data/customer_app.json` (2026-08-05),
    checked against Yash's exact reference window (Aug 1–5'26):**
    - **HOTO now reconciles closely: 222 (this pipeline, `project_state IN
      ('active','completed')`-scoped) vs his 226 (unfiltered `lead` table)** — a
      4-row gap, plausibly just the state filter. Much closer than step 2's HOTO
      figure.
    - **Order Booked does NOT reconcile: 44 (this pipeline) vs his 442 (unfiltered)
      — off by 10x.** Investigated and have a strong explanation, not yet
      confirmed with Yash: Order Booked is the *earliest* funnel milestone, and
      the monthly trend of `order_booked_at` in this pipeline's own data climbs
      steadily every month (July'26: 3,828) then falls off a cliff in Aug'26 (44)
      — because it's only 5 days into the month and most freshly-booked orders
      haven't yet matured into a `project` row with `project_state IN
      ('active','completed')` (some may have no project row yet at all). This is
      a **structural consequence of applying the same project_state filter to
      Order Booked as to the later-funnel milestones**, not a wrong field/table.
    - **Resolved 2026-08-05: Yash's explicit call — keep `project_state`
      filtering applied to Order Booked too, accept the 44 vs 442 gap for now.**
      Don't revisit without new information from him. This SQL/data change (both
      HOTO and Order Booked on `lead`) is ready to commit/push whenever asked —
      not yet pushed only because it hasn't been explicitly requested this
      session, not because anything is still unresolved.
- **Scheduled Customer App auto-pull is LIVE (2026-08-05):** `.github/workflows/
  pull_customer_app.yml` runs `scripts/pull_customer_app.py` at 9am/3pm/6pm/9pm IST
  daily, commits `data/customer_app.json` if changed. Confirmed working via a real
  run 2026-08-05 (after Yash fixed an initially-missing/misnamed repo secret —
  the script's CI error message was also made self-diagnosing for next time). If a
  local session's "CApp Data:" timestamp looks stale, that's normally just a
  `git pull` away from being current (local `Last-Modified` = on-disk mtime, not
  the original GitHub commit time) — not a sign the pipeline didn't run.
- **`Customer_App` REFERRAL sub-channel removed entirely 2026-08-05 (NOT the
  separate Metabase-sourced Customer App tabs above — different, unrelated
  thing, don't confuse the two).** Per Yash's explicit instruction, superseding
  an earlier reclassification plan (see Section 4). Applied locally to
  `Referral Dashboard.gs` (3 places: both `LEAD_DATA` CASE blocks, the lead
  query's `BQL_BASE` filter) and `index.html`/`index.preview.html`.
  **Two-step fix on the `index.html` side — the first step alone was
  incomplete, caught by Yash asking "does India Total still include
  Customer_App?":** (1) removed `'Customer_App'` from `SCS_ALL` (now 5
  entries) — but this only controls the filter dropdown/breakdown tables, NOT
  the underlying totals; (2) `ED_ALL`/`LD_ALL` themselves now exclude
  `sc==='Customer_App'` rows at ingestion (right where they're built from the
  raw JSON), which is what actually keeps them out of every India/city total,
  regardless of the BTL toggle or any other filter. Confirmed via console:
  `ED_ALL` 31,566 → 28,669 rows (exactly the prior `Customer_App` row count),
  zero remain in either array. Browser-tested across 7 tabs (incl. Digital,
  unaffected) — no lingering mentions, no console errors. **Two things still
  needed before this is fully live:**
  1. Yash must copy the updated `.gs` code into the actual Google Apps Script
     editor and redeploy — editing the tracked copy in this repo does nothing
     to the live script by itself.
  2. The `index.html` side needs the usual preview-review-merge cycle (it's
     currently only in `index.preview.html`, bundled with the Day on Day tab
     below — not yet committed to `index.html`/pushed).
  Historical `data/referral_effort.json`/`referral_leads.json` rows may still
  carry the old `Customer_App` tag until Yash redeploys the Apps Script — this
  is now harmless either way, since `ED_ALL`/`LD_ALL`'s own filter excludes
  them unconditionally regardless of what's still in the JSON.
- **⚠️ `index.preview.html` exists again and is now AHEAD of `index.html`** — a new
  4th Customer App tab, NOT yet reviewed/approved, do not merge/commit/push:
  - **`cappdod` → `bCAppDoD()` — "Day on Day."** One row per day of a **selected
    month** (`setCAppDoDMonth()`, trailing-12-months dropdown via `capGetMonths()`,
    defaults to the current month), with a **4-option stage picker** (Order
    Booked/HOTO/Installation/Commissioning, `setCAppDoDStage()`, defaults to
    Installation) — same 4 stages as Login Velocity's `CAPPVEL_STAGE_CFG` (widened
    2026-08-05 from an initial 3-way HOTO/Install/Comm picker after Yash asked for
    Order Booked too). Shows **both Ever Logged In and Logged In (At/After)** side
    by side (added after Yash's review — same pair as Login Velocity, for the same
    reason: "ever" alone hides pre-milestone logins). Own city multi-select filter
    (`cappdod-city`, defaults to unfiltered = India-wide, "All Cities" label per
    this dashboard's convention). Days beyond "today" in the *current* month show
    0 / "-" (no data exists yet for future dates) — a fully-elapsed past month just
    shows real data for every day. Full detail in Section 15.
  - **Verified against Yash's own reference numbers (screenshot, 2026-08-05) for
    Installation/Ever, current month:** Aug 1–4 daily figures matched exactly
    (83/42/50.6%, 83/52/62.7%, 44/25/56.8%, 102/46/45.1%). The small total-installs
    difference (315 vs his 312) is just newer data — 3 more installs landed on
    Aug 5 after his screenshot was taken, not a discrepancy. At/After, Order
    Booked/HOTO/Commissioning, and non-current months have no external reference
    yet.
  - Browser-tested: all 4 stages, month switching (confirmed a fully-elapsed past
    month like Jul'26 shows real data on every day, not zeros), city filter, and
    that month/stage selections persist independently of each other — no console
    errors. **Not yet shown to Yash for a second look.**
- **Everything else is committed and pushed** — confirm with `git fetch && git log
  --oneline origin/main..HEAD` (should be empty — the Day on Day tab above is the
  only thing currently sitting unmerged, in the gitignored preview file). The Apps
  Script pushes automated `data/*.json` refresh commits throughout the day (commit
  messages like "📊 Referral leads: ..."), and the Customer App auto-pull workflow
  does too ("Auto-refresh Customer App data from Metabase") — both routine, don't
  touch `index.html`/`CLAUDE.md`; a local push rejected because of either just
  needs `git pull --rebase origin main` before retrying, not a conflict investigation.
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

## 4. Referral sub-channels (now 5 — `Customer_App` removed entirely 2026-08-05)

| Sub-channel | Source |
|---|---|
| **Sales** | Leads generated by the Sales team |
| **Online** | Leads generated organically via WhatsApp / online channels |
| **BTL** | Leads generated by BTL teams via on-ground activities |
| **Ops / AMC** | Leads generated by Ops/AMC ground staff |
| **Referral_Others** | Other sources — HO team, self-employees, etc. |

**⚠️ History — read this before touching sub-channel logic again, the plan changed
mid-stream:** On 2026-08-03 a reclassification was planned (see old text, preserved
below) — remove the *current*, wrong `Customer_App` attribution but add back a
*correctly*-attributed `Customer_App`, carved out of `Online`. **That plan was
superseded 2026-08-05 by Yash's explicit, different instruction: remove
`Customer_App` entirely, don't pick it up from BigQuery at all, no mention of it
anywhere in the Referral flow.** This is a real removal now, not a reclassification
— don't reintroduce a `Customer_App` sub-channel without a fresh, explicit ask from
Yash, since the plan has already flipped once. Implemented 2026-08-05:
- **`Referral Dashboard.gs`** (local tracked copy in this repo) — removed
  `Source_Class LIKE '%Customer App%'` from all three places it appeared: the
  `Source_Class_final` CASE (both the effort-query and lead-query `LEAD_DATA` CTEs,
  ~2 occurrences each) which used to fold these rows into `'Referral'`; the
  `Source_Sub_Class_final` CASE which used to tag them `'Customer_App'`; and the
  lead-query's `BQL_BASE` CTE `WHERE` filter which used to pull these rows into the
  Referral base query at all. Now `Source_Class LIKE '%Customer App%'` rows fall to
  `Source_Class_final = 'Others'` and are excluded from the Referral pipeline
  entirely (not reclassified into any other Referral sub-channel).
  **⚠️ Editing this tracked `.gs` file does NOT change the live running Apps
  Script** — Yash still needs to copy the updated code into the actual Google Apps
  Script editor and save/redeploy it himself before this takes effect on real data.
  Until he does, live pulls will keep tagging Customer App-sourced leads as before.
- **`index.html`/`index.preview.html`** — removed `'Customer_App'` from `SCS_ALL`
  (now `['Sales','Online','BTL','Ops / AMC','Referral_Others']`, 5 entries).
  **This alone was NOT sufficient** — `SCS_ALL` only drives the sub-channel
  *filter dropdown* and breakdown-table iteration; it does not gate what counts
  toward India/city totals. `ED`/`LD` (used by every aggregate, including
  Executive Summary and India Summary's totals) are derived from `ED_ALL`/`LD_ALL`
  filtered *only* by the BTL toggle — so `Customer_App` rows already sitting in
  `data/referral_effort.json`/`referral_leads.json` were still silently flowing
  into every India/city total even after the dropdown fix, with no visible
  "Customer_App" row anywhere to reveal it. **Caught by Yash asking "does India
  Total still include Customer_App?" (2026-08-05) — confirmed yes, then fixed
  properly:** `ED_ALL`/`LD_ALL` themselves now drop `sc==='Customer_App'` rows at
  the point they're built from the raw JSON (`.filter(r=>...&&r.sc!=='Customer_App')`
  on both), so these rows can never enter any in-memory dataset the dashboard
  computes from, regardless of the BTL toggle or any other filter state — a hard,
  unconditional exclusion, not just a hidden-from-the-dropdown one. Confirmed via
  console: `ED_ALL` dropped from 31,566 to 28,669 rows (exactly the 2,897
  `Customer_App` rows previously in the data), zero `Customer_App` rows remain in
  either array, and all of Executive Summary/India Summary/Sub-Channel/Funnel/BQL
  Quality/Insights render with no lingering text and no console errors.
  **Lesson for next time a sub-channel (or similar dimension) needs removing:**
  filtering the constant array that drives dropdowns/breakdowns is not enough —
  check whether totals are computed from the *filtered* variable (`ED`/`LD`) or
  the *raw* one (`ED_ALL`/`LD_ALL`), and exclude at the raw-ingestion point if the
  goal is a true, complete removal.
- **Historical data note:** existing rows already in `data/referral_effort.json`/
  `referral_leads.json` may still carry the old `Customer_App` sub-channel tag
  until Yash redeploys the Apps Script — per the script's own changelog comment,
  every run does a full-history rewrite of these files (not an incremental
  append), so the next live run after redeployment will naturally regenerate
  fully-correct data. The `index.html` side's `ED_ALL`/`LD_ALL` filter above makes
  this a non-issue either way — even if stale `Customer_App` rows linger in the
  JSON files, the dashboard now excludes them unconditionally on load.
- `referral_mop.json` was never touched — no Sub-Channel MOP targets exist yet
  (Section 13), so there was nothing there to update.

**Original 2026-08-03 reclassification plan (superseded, kept for history only —
do not act on this without a fresh explicit ask):** the idea was to keep a
`Customer_App` sub-channel but carve it correctly out of `Online` (bifurcating
`Online` into two pieces), rather than removing it. Never implemented — the
2026-08-05 instruction above replaced this plan before any of it was built.

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
  unaggregated `SELECT` — confirmed 2026-08. **Two different fixes across two
  incidents, don't confuse them:**
  1. Originally (2026-08-03), passing `"constraints": {"max-results": 1000000,
     "max-results-bare-rows": 1000000}` in the query payload worked around it.
  2. **Metabase silently stopped honoring that override sometime around
     2026-08-18** — the cap came back with no error/warning, undercounting the
     Customer App pipeline by ~97% for ~1 day before Yash caught it via an
     obviously-wrong Login Velocity number. **Current fix (2026-08-19,
     confirmed working): use the CSV export endpoint (`/api/dataset/csv`)
     instead of the JSON one — it returns the full, uncapped result set with no
     constraints override needed at all**, and is what Metabase's own "Download
     results" button hits. Baked into `scripts/pull_customer_app.py`'s
     `run_metabase_query()` — if row counts ever look wrong again, re-run the
     diagnostic in that function's own comment before assuming anything else
     changed (don't just re-add the old constraints-override fix, it's proven
     not to be durable).

### Business logic (confirmed with Yash, 2026-08)
- **Login definition:** `otps` table, `"isVerified" = 'True'` AND `source IN
  ('CONSUMER', 'CUSTOMER_JOURNEY_TRACKER')`. **Not** `consumer_analytics` /
  `capp_login_successful` (an earlier, wrong guess — that table tracks Customer App
  UI events generally, but Yash's own established query uses `otps`).
- **Attribution chain:** `otps.mobile → customer.phone → customer.projects →
  customer_projects (index_=0) → projects_sseid → project.sseid`.
- **Milestone dates + city (current, as of the 2026-08-05 field correction —
  full history in Section 0 and the SQL file's own comments, don't re-litigate
  without new evidence from Yash):**
  - Order Booked = `lead.order_closure_datetime` (changed 2026-08-05, was
    `project.order_closure_datetime`)
  - HOTO = `lead.cx_approval_timestamp` (changed 2026-08-05, was
    `project.sales_handover_datetime`, which itself had replaced
    `project.cx_approval_timestamp` on 2026-08-04 — three different sourcings
    across two changes, see Section 0 for the full blow-by-blow)
  - Installation = `usertasks` task-`039A` completion timestamp (changed
    2026-08-04, was `project.installation_date`)
  - Commissioning = `project.commissioning_date` (never changed)
  - City = `project.site_address_cluster`
  - Lead ID = `project.lead_id`; **as of 2026-08-05 a `lead` join IS needed**
    (`LEFT JOIN lead l ON l.lead_id = p.lead_id`) for HOTO/Order Booked — this
    reverses the earlier "no lead join needed" note, which was accurate through
    2026-08-04 but is now stale.
- **2026-08-04 correction (superseded 2026-08-05 for HOTO, see below):** HOTO and
  Installation were switched to match Yash's Metabase question 1466 ("OMS Plants")
  after a numbers-don't-match-up check found card 1466 used different columns than
  this pipeline did. Installation → `usertasks` task-`039A` (kept, still current) —
  reconciled exactly against Yash's July'26 figure (3,581). HOTO →
  `p.sales_handover_datetime` — did NOT reconcile (3,949 vs his ~4,476), accepted
  as a working figure at the time, then superseded the next day (see below).
- **2026-08-05 correction (current):** Yash gave a further, explicit instruction —
  backed by his own `COUNT(*)` reference queries against `public.lead` — to source
  **HOTO from `lead.cx_approval_timestamp`** (same field name as the pre-08-04
  choice, but off `lead` not `project` — genuinely different data) and **Order
  Booked from `lead.order_closure_datetime`** (same field name as before, also
  now off `lead` not `project`). Reconciled against his reference window
  (Aug 1–5'26, `>= '2026-08-01' AND < '2026-08-06'`):
  - **HOTO: 222 (this pipeline) vs his 226 (unfiltered)** — close, a 4-row gap
    plausibly just the `project_state` filter. A big improvement over the
    08-04 HOTO figure.
  - **Order Booked: 44 (this pipeline) vs his 442 (unfiltered) — off by 10x.**
    Investigated: this pipeline's own `order_booked_at` trend climbs every month
    (Jul'26: 3,828) then falls off a cliff in Aug'26 (44, only 5 days into the
    month at analysis time) — because Order Booked is the *earliest* funnel
    milestone, and most freshly-booked orders haven't yet matured into a
    `project` row with `project_state IN ('active','completed')`. This looks
    like a structural consequence of applying the same state filter to an
    early-funnel milestone, not a wrong field — **but this has NOT been
    confirmed with Yash, and the change is NOT committed/pushed pending that.**
    Open question for him: is `project_state` filtering even meaningful for
    Order Booked, or should it be reported unfiltered (a bigger query change,
    not just a field swap)?
  - Login source stays `IN ('CONSUMER', 'CUSTOMER_JOURNEY_TRACKER')` — unchanged
    by this round of correction.
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
  `.metabase_key/` for local/manual runs, or from a `METABASE_API_KEY` env var when
  running in CI (added 2026-08-04 — see the scheduled workflow below), runs the query
  above via Metabase's API (with the row-cap fix), applies the city merge +
  null-city drop, writes `data/customer_app.json`.
- **Scheduled auto-pull — LIVE as of 2026-08-05, per Yash's request.**
  `.github/workflows/pull_customer_app.yml` runs the puller script 4x/day at 9:00 AM,
  3:00 PM, 6:00 PM, 9:00 PM **IST** (cron times are in UTC: `30 3 * * *`, `30 9 * * *`,
  `30 12 * * *`, `30 15 * * *` — IST is UTC+5:30) and commits `data/customer_app.json`
  if it changed, rebasing onto `main` first to avoid racing the Referral Apps
  Script's own automated pushes (same race this session already hit manually once —
  see the note on that above). Also has a `workflow_dispatch` trigger for a manual
  run from the Actions tab.
  - Yash added the required `METABASE_API_KEY` repo secret himself (Settings →
    Secrets and variables → Actions) — Claude has no access to repo secrets and
    never read/printed the actual key value at any point.
  - Committed and pushed 2026-08-05 (commit `41bf777`), after Yash's explicit
    go-ahead — treated as a standing/persistent automation requiring that
    confirmation before going live, same discipline as `index.html` changes.
  - **Not yet verified end-to-end in a real Actions run** — only checked for YAML
    validity locally (`pyyaml.safe_load`) before pushing, since a real run needs the
    secret in place. If Customer App data ever looks stale, check the workflow's run
    history in the repo's Actions tab (or trigger a manual `workflow_dispatch` run)
    before assuming the pipeline is broken — don't just re-diagnose from scratch.
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
- **Not yet built (as of Phase 3):** nothing else was explicitly flagged as in-scope
  for Phase 3 — confirm with Yash before assuming it's fully "done" rather than just
  "the two things he asked for are built."

- **4th tab: `cappdod` → `bCAppDoD()` — "Day on Day" (2026-08-05, per Yash's
  request — built in `index.preview.html`, not yet merged/re-reviewed).** Daily
  (not cumulative) milestone-cohort counts vs Customer App login counts, one row
  per calendar day of a **selected month**.
  - **Stage picker, 4 options** (`CAPPDOD_STAGE_CFG`: Order Booked/HOTO/
    Installation/Commissioning, `setCAppDoDStage()`) — same 4 stages as Login
    Velocity's `CAPPVEL_STAGE_CFG`. Started as a 3-way HOTO/Install/Comm picker
    (matching the MoM Trend tab's own selector) but widened to include Order
    Booked after Yash asked for it explicitly. Defaults to Installation (the
    original ask). Cohort for day D under a given stage = projects whose that
    stage's date field falls on that calendar day.
  - **Month selector, added 2026-08-05** (`setCAppDoDMonth()`, trailing 12 months
    via the shared `capGetMonths()` helper, defaults to the current month). Days
    beyond "today" in the *current* month show 0/"-" (no data exists yet for
    future dates, nothing special-cased) — a fully-elapsed past month just shows
    real data for every day, confirmed by testing Jul'26 (every day non-zero,
    including the 31st). Month and stage selections are independent state and
    persist across each other's changes.
  - **Both login-rate definitions shown side by side, added 2026-08-05 per Yash's
    review** (top summary cards AND both table column-pairs) — **Ever Logged In**
    (any time, including before reaching the stage) and **Logged In (At/After)**
    (only counting logins on/after the stage's date, the stricter subset). Same
    pair, same reasoning, as the Login Velocity tab. For Installation specifically
    the gap between the two is large (e.g. Aug 1'26: 83 installs, 42 ever logged in
    but only 3 at/after) — most Customer App logins happen well before installation
    (e.g. right after Order Booked/HOTO), so this split matters a lot here.
  - Own city multi-select filter (`cappdod-city`, `CAPP_ALL_CITIES` options,
    `CAPP_CITY_CFG` — same widget/pattern as the other 3 tabs). Default
    (unfiltered) shows India-wide totals, labeled "All Cities" per this dashboard's
    own convention — Yash's own reference spreadsheet for this feature literally
    labeled its equivalent dropdown "India," but consistency with the other 3
    Customer App tabs' wording was judged more valuable than matching that exact
    label.
  - Top summary cards (Total <stage> / Ever Logged In % / Logged In At/After % for
    the selected month) above the daily table, computed by summing the same
    per-day figures — not a separate calculation.
  - **Verified against Yash's own reference numbers (a screenshot of his working
    spreadsheet, 2026-08-05) for the Installation stage's "Ever" column, current
    month:** Aug 1–4 daily figures matched exactly — 83/42/50.6%, 83/52/62.7%,
    44/25/56.8%, 102/46/45.1%. Total installs differed slightly (this pipeline:
    315, his screenshot: 312) — accounted for by 3 more installs landing on Aug 5
    after his screenshot was taken (his screenshot's own Aug 5 row showed 0), not
    a data or logic discrepancy. The "At/After" column, Order Booked/HOTO/
    Commissioning, and non-current months have no external reference yet.
  - Browser-tested: all 4 stages produce distinct correct numbers, city filter
    narrows correctly (e.g. Pune-only, Installation stage, Aug 1: 14/9/64.3%
    ever), month switching (Jul'26 shows real non-zero data through the 31st) —
    no console errors.
