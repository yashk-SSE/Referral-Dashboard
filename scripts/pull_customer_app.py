#!/usr/bin/env python3
"""
Customer App data puller -- Metabase -> data/customer_app.json

Runs the query in scripts/customer_app_query.sql (single source of truth,
shared with the independent Metabase SQL question Yash can run himself)
against the SolarSquare Postgres database via Metabase's API, and writes the
per-project rows to data/customer_app.json for the dashboard.

One row per PROJECT (not per login event, and not just projects with a
login) -- includes every project in `project`, with first_login_at = null
for the ones that have never logged in. This is required to compute "% of
commissioned/installed/HOTO base that has logged in" against the full base,
not just the subset that ever logged in. Only the FIRST login per project is
tracked, not every login -- confirmed with Yash, 2026-08.

Milestone-window bucketing and P50/P90/P95/Avg stats are computed downstream
in the dashboard's JavaScript, not here -- this script only pulls raw data.

Requires .metabase_key/metabase_key.txt (gitignored, never committed) with
the raw API key on its own line. Nothing in this script is a secret.
"""
import json
import os
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


def load_api_key():
    with open(KEY_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_query():
    with open(QUERY_FILE, "r", encoding="utf-8") as f:
        return f.read()


def run_metabase_query(api_key, sql):
    # Metabase's /api/dataset defaults to a ~2000-row display cap even for a
    # plain SELECT with no LIMIT -- this override is required to get the full
    # result set instead of a silently truncated one. Confirmed 2026-08:
    # without this, a 116,666-row query silently came back as exactly 2,000.
    url = f"{METABASE_BASE_URL}/api/dataset"
    payload = json.dumps({
        "database": DATABASE_ID,
        "type": "native",
        "native": {"query": sql},
        "constraints": {"max-results": 1000000, "max-results-bare-rows": 1000000},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("x-api-key", api_key)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("=" * 60)
    print("Customer App Data Puller (Metabase)")
    print("=" * 60)

    api_key = load_api_key()
    sql = load_query()

    print("Running query against Metabase...")
    result = run_metabase_query(api_key, sql)

    if "data" not in result:
        print("ERROR: unexpected response from Metabase:")
        print(json.dumps(result, indent=2)[:2000])
        raise SystemExit(1)

    cols = [c["name"] for c in result["data"]["cols"]]
    rows = result["data"]["rows"]
    print(f"Fetched {len(rows):,} rows. Columns: {cols}")

    all_records = [dict(zip(cols, row)) for row in rows]

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

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, default=str)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\nWrote {OUTPUT_FILE} -- {len(records):,} rows -- {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
