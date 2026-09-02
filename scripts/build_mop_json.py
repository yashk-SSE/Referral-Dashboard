#!/usr/bin/env python3
"""
Build data/referral_mop.json from a monthly "MOP <Mon> Referral.xlsx" file.

WHY THIS EXISTS
---------------
referral_mop.json has always been maintained by hand (it is the one file in
data/ that no pipeline produces). From Sep'26 the source workbook carries a
3-way sub-channel split instead of the old 2-way BTL split, which is too many
numbers to retype safely every month -- hence this script.

SOURCE LAYOUT (Sep'26 onward)
-----------------------------
Row 1: metric group headers (BQL / MS / MD / Order / HOTO)
Row 2: sub-headers, 4 per metric: Total (Sales+Non-Sales) | Sales | Non Sales | BTL Referral
Row 3+: one row per city, col A = city name, "India" first.
A blank spacer column sits between metric groups, so each metric block starts
5 columns after the previous one (B, G, L, Q, V).

OUTPUT SCHEMA
-------------
Per city: sales / nonSales / btl / noBtl / combined, each {BQL,MS,MD,ORDER,HOTO}.

  noBtl    = the workbook's own "Total (Sales+Non-Sales)" column, taken AS GIVEN
             (not recomputed as sales+nonSales -- see ROUNDING below)
  combined = noBtl + btl

`noBtl`/`btl`/`combined` keep the exact names the pre-Sep'26 dashboard loader
already reads, so an old build of index.html consumes this file unchanged;
`sales`/`nonSales` are purely additive.

ROUNDING
--------
The workbook rounds every column independently, so "Total (Sales+Non-Sales)"
disagrees with sales+nonSales by +/-1 in ~19% of cells, and the India row
disagrees with the sum of its cities by 1-3. Both are inherent to the source
model, not transcription error. This script preserves the workbook's own
figures verbatim and reports the deltas rather than silently reconciling them
-- if that call ever changes, flip SUM_TOTALS below.
"""
import json, sys, argparse
from pathlib import Path
import openpyxl

METRICS = ['BQL', 'MS', 'MD', 'ORDER', 'HOTO']
# First column of each metric's 4-column block (1-indexed): B, G, L, Q, V
METRIC_COL = {'BQL': 2, 'MS': 7, 'MD': 12, 'ORDER': 17, 'HOTO': 22}
# Offsets within a metric block
OFF = {'noBtl': 0, 'sales': 1, 'nonSales': 2, 'btl': 3}

# False = trust the workbook's "Total (Sales+Non-Sales)" column (default).
# True  = recompute noBtl as sales+nonSales so the parts always add up.
SUM_TOTALS = False

CITY_RENAME = {'Bengaluru': 'Bangalore'}


def num(v):
    if v is None or v == '':
        return 0
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return 0


def parse(xlsx_path, sheet=None):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]

    # Sanity-check the header layout before trusting the hardcoded columns --
    # a shifted/renamed column would otherwise silently produce wrong targets.
    for m, col in METRIC_COL.items():
        got = str(ws.cell(row=1, column=col).value or '').strip().upper()
        if got != m.upper() and not (m == 'ORDER' and got == 'ORDER'):
            raise SystemExit(
                f'Unexpected layout: expected metric "{m}" in row 1 col {col}, found "{got}". '
                'The workbook column layout changed -- update METRIC_COL.')
        sub = str(ws.cell(row=2, column=col + OFF['btl']).value or '').strip().lower()
        if 'btl' not in sub:
            raise SystemExit(
                f'Unexpected layout: expected a BTL sub-header at row 2 col {col + OFF["btl"]}, '
                f'found "{sub}".')

    rows, warnings = [], []
    for r in range(3, ws.max_row + 1):
        raw = ws.cell(row=r, column=1).value
        if raw is None or not str(raw).strip():
            continue
        city = str(raw).strip()
        city = CITY_RENAME.get(city, city)

        blocks = {k: {} for k in ('sales', 'nonSales', 'btl', 'noBtl')}
        for m in METRICS:
            base = METRIC_COL[m]
            for key, off in OFF.items():
                blocks[key][m] = num(ws.cell(row=r, column=base + off).value)

        for m in METRICS:
            parts = blocks['sales'][m] + blocks['nonSales'][m]
            if SUM_TOTALS:
                blocks['noBtl'][m] = parts
            elif parts != blocks['noBtl'][m]:
                warnings.append((city, m, blocks['noBtl'][m], blocks['sales'][m],
                                 blocks['nonSales'][m], parts))

        blocks['combined'] = {m: blocks['noBtl'][m] + blocks['btl'][m] for m in METRICS}

        rows.append({'city': city, 'sales': blocks['sales'], 'nonSales': blocks['nonSales'],
                     'btl': blocks['btl'], 'noBtl': blocks['noBtl'],
                     'combined': blocks['combined']})
    return rows, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('xlsx')
    ap.add_argument('-o', '--out', default='data/referral_mop.json')
    ap.add_argument('--sheet', default=None)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    rows, warnings = parse(a.xlsx, a.sheet)
    if not rows:
        raise SystemExit('No city rows parsed -- aborting rather than writing an empty MOP file.')
    if rows[0]['city'] != 'India':
        print(f'WARNING: first row is "{rows[0]["city"]}", not "India".', file=sys.stderr)

    print(f'Parsed {len(rows)} rows ({len(rows) - 1} cities + India) from {a.xlsx}')
    if warnings:
        print(f'\n{len(warnings)} cells where "Total (Sales+Non-Sales)" != sales+nonSales '
              f'(workbook rounding, preserved as given):')
        for city, m, tot, s, ns, parts in warnings:
            print(f'   {city:<12} {m:<6} Total={tot:<6} Sales={s:<6} NonSales={ns:<6} '
                  f'sum={parts:<6} ({parts - tot:+d})')

    india = rows[0]
    print('\nIndia targets:')
    print(f'  {"":<10} ' + ' '.join(f'{m:>7}' for m in METRICS))
    for k in ('sales', 'nonSales', 'btl', 'noBtl', 'combined'):
        print(f'  {k:<10} ' + ' '.join(f'{india[k][m]:>7}' for m in METRICS))

    if a.dry_run:
        print('\n--dry-run: nothing written.')
        return
    Path(a.out).write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    print(f'\nWrote {a.out} ({len(rows)} rows)')


if __name__ == '__main__':
    main()
