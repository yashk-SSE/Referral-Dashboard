#!/usr/bin/env python3
"""
Seed data/referral_mop_history.json from historical versions of referral_mop.json.

WHY THIS EXISTS
---------------
referral_mop.json only ever holds the CURRENT month's targets and is overwritten
whenever a new workbook lands, so past months survived only inside git history.
The "Last Month Performance" dashboard tab needs them at runtime, so
build_mop_json.py now maintains a month-keyed history file going forward -- and
this script backfills the months that predate it, straight out of git so the
provenance of every figure is a commit hash rather than a retyped number.

Re-runnable: it replaces the months it knows about and leaves any others alone.

WHAT IS RECOVERABLE (audited 2026-09-03)
----------------------------------------
The file's schema changed twice, so not every past month is usable:

  2026-09  ca3f513  5 blocks: sales/nonSales/btl/noBtl/combined   -> all 5 variants
  2026-08  94fb5c3  3 blocks: noBtl/btl/combined                  -> 3 variants
  2026-07  db6a526  FLAT (BQL/MS/MD/ORDER/HOTO, no blocks)         -> combined only
  2026-06  ed2f908  FLAT, and NO ORDER field                       -> UNUSABLE
  2026-05  b9fe8a2  FLAT, and NO ORDER field                       -> UNUSABLE

June and earlier predate the explicit Order target. The whole analysis is an
Order-deficit decomposition, so there is nothing to bridge to -- those months are
deliberately excluded rather than half-loaded.

A flat month is mapped to the `combined` block only. Note its "All" is not
composition-comparable to a later month's "All": no BTL split existed then, so
whatever BTL volume it contains is baked in undifferentiated.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_mop_json import METRICS, write_history, month_label  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

# month -> (commit, note). Only months whose schema supports the Order bridge.
SOURCES = [
    ('2026-07', 'db6a526', 'flat schema, no BTL split -- combined view only'),
    ('2026-08', '94fb5c3', 'noBtl/btl/combined'),
    ('2026-09', 'ca3f513', 'sales/nonSales/btl/noBtl/combined'),
]

CITY_RENAME = {'Bengaluru': 'Bangalore'}
BLOCKS = ('sales', 'nonSales', 'btl', 'noBtl', 'combined')


def git_show(commit, path):
    out = subprocess.run(['git', 'show', f'{commit}:{path}'],
                         cwd=str(REPO_ROOT), capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f'git show {commit}:{path} failed: '
                         f'{out.stderr.decode("utf-8", "replace").strip()}')
    return json.loads(out.stdout.decode('utf-8'))


def normalise(raw):
    """Any historical shape -> the current per-city block shape.

    Two shapes exist: block-based (noBtl/btl/combined, optionally with
    sales/nonSales) and flat, where the metrics sit directly on the row. Flat
    rows become a `combined` block, since that is what they represent.
    """
    rows = []
    for r in raw:
        city = str(r.get('city') or r.get('City') or '').strip()
        if not city:
            continue
        city = CITY_RENAME.get(city, city)
        out = {'city': city}
        if any(isinstance(r.get(b), dict) for b in BLOCKS):
            for b in BLOCKS:
                if isinstance(r.get(b), dict):
                    out[b] = {m: int(r[b].get(m) or 0) for m in METRICS}
        else:
            # Flat month. ORDER is required -- without it there is no bridge.
            if not any(k in r for k in ('ORDER', 'Order')):
                return None
            out['combined'] = {m: int(r.get(m) or r.get(m.title()) or 0) for m in METRICS}
        rows.append(out)
    # India first, matching the current file's convention.
    rows.sort(key=lambda x: (x['city'] != 'India',))
    return rows


def main():
    print('Backfilling %s from git\n' % 'data/referral_mop_history.json')
    for ym, commit, note in SOURCES:
        raw = git_show(commit, 'data/referral_mop.json')
        rows = normalise(raw)
        if rows is None:
            print(f'  {ym}  {commit}  SKIPPED -- no ORDER field, bridge impossible')
            continue
        hist = write_history(rows, ym, quiet=True)
        india = next((c for c in rows if c['city'] == 'India'), {})
        comb = india.get('combined', {})
        print(f'  {ym}  {commit}  {len(rows):>2} rows  '
              f'variants={",".join(hist["months"][ym]["variants"]):<38} '
              f'India Order={comb.get("ORDER", "-"):<5} HOTO={comb.get("HOTO", "-"):<5} '
              f'({note})')

    p = REPO_ROOT / 'data' / 'referral_mop_history.json'
    hist = json.loads(p.read_text(encoding='utf-8'))
    print(f'\n{p.name}: {len(hist["months"])} months -> '
          f'{", ".join(f"{k} ({v['label']})" for k, v in hist['months'].items())}')
    print(f'size: {p.stat().st_size / 1024:.1f} KB')


if __name__ == '__main__':
    main()
