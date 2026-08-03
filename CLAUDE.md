# SolarSquare Referral Dashboard — Project Context

> **Read this file in full before touching any code.** It contains business logic that is
> NOT obvious from the codebase and cannot be reverse-engineered from the data alone.
> `README.md` was a stale 1-line stub as of the first session (2026-08-03) and has since
> been rewritten to summarize this project properly. As of 2026-08-03, keeping both this
> file and `README.md` in sync with the actual code is a standing habit (see Section 12)
> — if a future session finds either one stale again, fix it as part of that session's
> work, don't just flag it and move on.

---

## 1. What this project is

A single-file HTML/JavaScript dashboard tracking the **Referral sales channel** funnel
performance for SolarSquare, a B2C solar company, across 29–32 Indian cities (see
**Section 6 — flagged discrepancy** on exact count/list).

- Deployed on **Netlify**, sourced from this GitHub repo: `yashk-SSE/Referral-Dashboard`
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
- **Possible future direction (not scheduled, no timeline):** Yash may eventually move the
  data pipeline back to Python/GitHub Actions, and separately connect this project to
  **Metabase**. Neither is happening now — flagged here so a future session doesn't have
  to rediscover the context. Don't build toward this speculatively.

### Known local files — confirmed by inspection (2026-08-03)

| Name | Type | Confirmed role |
|---|---|---|
| `.github/workflows/test.yml` | workflow | Trivial — `echo` on manual dispatch only. Not a real test/CI gate. |
| `.github/workflows/update_data.yml` | — | **Deleted** (was the killed Python pipeline's trigger). |
| `data/` | folder | 5 JSON files written by the Apps Script: `referral_effort.json`, `referral_leads.json`, `digital_effort.json`, `digital_leads.json`, `referral_mop.json`. First four are BigQuery-generated; `referral_mop.json` (MOP targets) is maintained separately/manually — not produced by any script in this repo. |
| `scripts/` | folder | **Emptied** — `fetch_data.py` deleted (killed pipeline). |
| `index.html` | 664 KB | The dashboard. 7,254 lines, single file, everything inline. Handles Referral **and** Digital channels plus a Ref-vs-Digital compare view (not Referral-only, despite Section 1's old framing). |
| `README.md` | — | Was outdated 1-line stub; now kept in sync with this file (see Section 12). |
| `Referral Dashboard.gs` | 32 KB | Apps Script v5. Queries BigQuery for **both** Referral and Digital (effort + lead-level), pushes each JSON straight to `main` via GitHub's API. This is the live, authoritative pipeline. |
| `referral-dashboard` | 1 byte, no extension | Confirmed: a single newline, no content, no function. Not a config or script. Recommend deleting as dead weight — not yet done, flagging for your call (see Section 13). |

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

## 4. Referral sub-channels (6)

| Sub-channel | Source |
|---|---|
| **Sales** | Leads generated by the Sales team |
| **Online** | Leads generated organically via WhatsApp / online channels |
| **BTL** | Leads generated by BTL teams via on-ground activities |
| **Ops / AMC** | Leads generated by Ops/AMC ground staff |
| **Customer_App** | Leads generated directly by customers via the Customer App |
| **Referral_Others** | Other sources — HO team, self-employees, etc. |

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
- `referral-dashboard` (empty, 1-byte, no-extension file at repo root) — recommend
  deleting, not yet done. Confirm before removing since it's presumably already
  tracked in the GitHub repo's history.
- Possible future pipeline migration to Python/GitHub Actions + Metabase — see
  Section 1. Not scheduled, no timeline, don't build toward it yet.

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
