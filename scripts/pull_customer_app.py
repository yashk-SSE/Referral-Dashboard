#!/usr/bin/env python3
"""
Customer App data puller -- Metabase -> data/customer_app.json

Runs the query in scripts/customer_app_query.sql (single source of truth,
shared with the independent Metabase SQL question Yash can run himself)
against the SolarSquare Postgres database via Metabase's API, and writes the
per-project rows to data/customer_app.json for the dashboard.

One row per PROJECT (not per login event, and not just projects with a
login) -- includes every project with project_state IN ('active','completed')
(cancelled/on-hold/seeking-cancellation excluded, per Yash 2026-08), with
first_login_at = null for the ones that have never logged in. This is
required to compute "% of commissioned/installed/HOTO base that has logged
in" against the full base, not just the subset that ever logged in. Only the
FIRST login per project is tracked, not every login -- confirmed with Yash,
2026-08.

Milestone-window bucketing and P50/P90/P95/Avg stats are computed downstream
in the dashboard's JavaScript, not here -- this script only pulls raw data.

Requires .metabase_key/metabase_key.txt (gitignored, never committed) with
the raw API key on its own line. Nothing in this script is a secret.
"""
import csv
import io
import json
import os
import urllib.parse
import urllib.request

METABASE_BASE_URL = "https://metabase-lighthouse.solarsquare.in"
DATABASE_ID = 2  # "SolarSquare" Postgres database, per Metabase's /api/database

# City-name reconciliation vs the Referral dashboard's existing city/tier list,
# confirmed with Yash 2026-08. "Bengaluru" is the same known remap already
# applied to Referral data. Raipur and Surat are deliberately NOT merged --
# Raipur is a genuinely new city (expected to join the Referral dashboard's
# own tier list next month), Surat is a discontinued city kept as its own
# distinct (inactive) bucket rather than folded into anywhere else.
# Ghaziabad/Faridabad don't appear under those names anywhere in `project` as
# of 2026-08 (checked, including name-variant search) -- these two mappings
# are defensive/forward-looking, in case they show up in a future pull.
# Ahilyanagar has no mapping at all -- left out entirely for now, per Yash.
CITY_MERGE_MAP = {
    "Bengaluru": "Bangalore",
    "Ajmer": "Jaipur",
    "Baroda": "Ahmedabad",
    "Mysuru": "Bangalore",
    "Salem": "Bangalore",
    "Ghaziabad": "Noida",
    "Faridabad": "Gurgaon",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
KEY_FILE = os.path.join(REPO_ROOT, ".metabase_key", "metabase_key.txt")
QUERY_FILE = os.path.join(SCRIPT_DIR, "customer_app_query.sql")
OUTPUT_FILE = os.path.join(REPO_ROOT, "data", "customer_app.json")

# Sanity-check thresholds for the integrity guard below -- a refresh that comes
# back with this much less data than the previous one is treated as a broken
# pull, not as real movement. Both figures only ever grow by a few hundred a
# day, so 20% is a wide margin that still catches a total collapse.
MAX_DROP = 0.20


def load_api_key():
    # CI (GitHub Actions) has no .metabase_key/ checkout -- it supplies the key via
    # the METABASE_API_KEY secret/env var instead. Local/manual runs keep using the
    # gitignored key file. Never log or print the value either way.
    env_key = os.environ.get("METABASE_API_KEY")
    if env_key:
        return env_key.strip()
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Fail with a message that actually points at the fix, instead of a bare
        # FileNotFoundError for a path that was never expected to exist in CI --
        # confirmed 2026-08-05 this is exactly what happens when the secret is
        # missing/misnamed/empty (a 2026-08-04 run failed this way).
        raise SystemExit(
            "METABASE_API_KEY is not set (or is empty) in this GitHub Actions run. "
            "Check Settings > Secrets and variables > Actions > Repository secrets "
            "for a secret named exactly METABASE_API_KEY (case-sensitive, no extra "
            "spaces) -- Environment/Codespaces/Dependabot secrets don't count here."
        )
    with open(KEY_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_query():
    with open(QUERY_FILE, "r", encoding="utf-8") as f:
        return f.read()


def run_metabase_query(api_key, sql):
    # Metabase's /api/dataset defaults to a ~2000-row display cap even for a
    # plain SELECT with no LIMIT. Passing a "constraints": {"max-results": ...}
    # override in the JSON payload used to work around this (confirmed 2026-08),
    # but Metabase silently stopped honoring it at some point between the
    # 2026-08-18 09:59 UTC and 13:24 UTC scheduled pulls -- every /api/dataset
    # call since then came back hard-capped at exactly 2,000 rows again
    # (confirmed 2026-08-19: `json_query.constraints` in the response was `None`
    # even though we sent it, i.e. Metabase/the API gateway now drops the field
    # entirely rather than just ignoring its value). This resurfaced as a real
    # data bug -- Customer App tabs showing ~226 installs pan-India instead of
    # the true ~60k population.
    #
    # Fix: use the CSV export endpoint (/api/dataset/csv) instead of the JSON
    # one (/api/dataset). Confirmed 2026-08-19 this returns the FULL result set
    # uncapped (60,244 rows vs a plain COUNT(*) of 60,244) with no constraints
    # override needed at all. This is also what Metabase's own UI "Download
    # results" button hits, so it's a first-class, intentionally-uncapped path,
    # not a hack. If this ever regresses again, re-run the 4-query diagnostic
    # (bare COUNT(*), bare SELECT via /api/dataset, bare SELECT via
    # /api/dataset/csv) before assuming anything else changed.
    url = f"{METABASE_BASE_URL}/api/dataset/csv"
    payload = {"database": DATABASE_ID, "type": "native", "native": {"query": sql}}
    body = urllib.parse.urlencode({"query": json.dumps(payload)}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("x-api-key", api_key)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=240) as resp:
        csv_text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(csv_text)))


def check_before_write(records, with_login):
    """Refuse to overwrite customer_app.json with an obviously-broken pull.

    Both failures this pipeline has actually hit were SILENT -- Metabase kept
    returning HTTP 200 and this script kept writing a perfectly valid JSON file:

      1. 2026-08-18 -- Metabase quietly stopped honoring the constraints
         override and re-capped results at 2,000 rows (~97% of the base
         missing). Caught only because a Login Velocity number looked absurd.
      2. 2026-08-27 -- phone masking landed on otps.mobile but NOT on
         customer.phone, so the otps -> customer join matched nothing and
         first_login_at came back NULL for every project. That ran for 6.5 days
         across all four Customer App tabs before anyone noticed. (Fixed on
         2026-09-03 when customer.phone was masked with the same salt.)

    Neither raised an error, so this guard checks the two numbers that would
    have caught them, and exits non-zero rather than committing bad data. On
    failure the existing data/customer_app.json is left untouched, so the
    dashboard keeps serving the last known-good pull instead of zeros.

    Set ALLOW_DATA_DROP=1 (env var) to push through a drop that's genuinely
    expected -- e.g. a deliberate change to the project_state filter.
    """
    problems = []

    if not records:
        problems.append("the query returned 0 rows")

    if records and with_login == 0:
        problems.append(
            f"0 of {len(records):,} projects have a login -- check whether "
            "otps.mobile and customer.phone are still masked the same way "
            "(see CLAUDE.md Section 15)"
        )

    prev = None
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                prev = json.load(f)
        except (OSError, ValueError) as e:
            print(f"WARNING: couldn't read the previous {OUTPUT_FILE} to compare "
                  f"against ({e}) -- skipping the drop check for this run.")

    if prev:
        prev_rows = len(prev)
        prev_logins = sum(1 for r in prev if r.get("first_login_at"))
        print(f"Previous pull for comparison: {prev_rows:,} projects, "
              f"{prev_logins:,} with a login")

        if prev_rows and len(records) < prev_rows * (1 - MAX_DROP):
            drop = (1 - len(records) / prev_rows) * 100
            problems.append(f"project count fell {drop:.1f}% -- {prev_rows:,} "
                            f"-> {len(records):,}")

        if prev_logins and with_login < prev_logins * (1 - MAX_DROP):
            drop = (1 - with_login / prev_logins) * 100
            problems.append(f"projects with a login fell {drop:.1f}% -- "
                            f"{prev_logins:,} -> {with_login:,}")

    if not problems:
        return

    summary = "\n".join(f"  - {p}" for p in problems)
    if os.environ.get("ALLOW_DATA_DROP") == "1":
        print(f"\nData check flagged:\n{summary}\n"
              "ALLOW_DATA_DROP=1 is set -- writing anyway.")
        return

    raise SystemExit(
        f"\nABORT: this pull looks broken, so {OUTPUT_FILE} was NOT overwritten:\n"
        f"{summary}\n\n"
        "Diagnose before re-running -- don't just re-run and hope. Check the\n"
        "join in scripts/customer_app_query.sql against the current state of\n"
        "the Metabase views, then set ALLOW_DATA_DROP=1 if the drop is real."
    )


def main():
    print("=" * 60)
    print("Customer App Data Puller (Metabase)")
    print("=" * 60)

    api_key = load_api_key()
    sql = load_query()

    print("Running query against Metabase...")
    all_records = run_metabase_query(api_key, sql)

    if not all_records:
        print("ERROR: Metabase returned zero rows (or an unparseable response).")
        raise SystemExit(1)

    print(f"Fetched {len(all_records):,} rows. Columns: {list(all_records[0].keys())}")

    # CSV round-trips booleans as the strings "true"/"false", and SQL NULLs as ""
    # rather than a real null -- normalize both back to what the JSON pipeline
    # used to produce, so the dashboard's existing null/boolean checks stay simple.
    date_fields = ("order_booked_at", "hoto_at", "installation_at", "commissioning_at", "first_login_at")
    for r in all_records:
        r["date_anomaly"] = str(r.get("date_anomaly")).strip().lower() == "true"
        for f in date_fields:
            if r.get(f) == "":
                r[f] = None

    # Drop rows with no real city -- per Yash, these should not appear in any
    # city-level breakdown rather than show up as a fake "blank" bucket.
    # NOTE: at least one source row has the literal 4-character string "None"
    # stored in site_address_cluster (not a true SQL NULL) -- confirmed 2026-08,
    # treat it the same as missing.
    def has_real_city(r):
        c = r.get("city")
        return bool(c) and c.strip().lower() != "none"

    null_city_count = sum(1 for r in all_records if not has_real_city(r))
    records = [r for r in all_records if has_real_city(r)]
    if null_city_count:
        print(f"Dropped {null_city_count:,} row(s) with no real city set")

    # Apply the confirmed city merge map.
    for r in records:
        r["city"] = CITY_MERGE_MAP.get(r["city"], r["city"])

    anomalies = sum(1 for r in records if r.get("date_anomaly"))
    print(f"Flagged {anomalies:,} rows with date_anomaly = true "
          f"(commissioning_at before installation_at)")

    with_login = sum(1 for r in records if r.get("first_login_at"))
    print(f"{len(records):,} total projects, {with_login:,} have at least one "
          f"login ({with_login/len(records)*100:.1f}%)")

    distinct_cities = sorted(set(r["city"] for r in records if r.get("city")))
    print(f"{len(distinct_cities)} distinct city values after merging:")
    for c in distinct_cities:
        print(f"  - {c}")

    # Last line of defence before we clobber the previous good file -- see the
    # function's docstring for the two silent failures this exists to catch.
    check_before_write(records, with_login)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, default=str)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\nWrote {OUTPUT_FILE} -- {len(records):,} rows -- {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
