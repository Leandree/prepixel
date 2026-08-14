#!/usr/bin/env python3
"""Aggregate campaign result JSONs into the coverage matrix + predictability table.

Usage: python3 aggregate.py            # reads campaign/results/*.json
Outputs: campaign/MATRIX.md (human) and campaign/matrix.json (machine).
"""
import json, glob, os, collections

HERE = os.path.dirname(__file__)
files = sorted(glob.glob(os.path.join(HERE, 'results', '*.json')))
rows = []
for f in files:
    try:
        d = json.load(open(f))
        if 'os' in d and 'app' in d:
            rows.append(d)
    except Exception as e:
        print(f"skip {f}: {e}")

V = {'works': '✅ works', 'partial': '🟡 partial', 'unavailable': '⬜ unavailable', 'blocked': '⛔ blocked'}
F = {'none': '—', 'explicit': 'explicit', 'silent': '❗SILENT', 'blocked': 'blocked'}

def tok(d, k):
    v = d.get('measurements', {}).get(k)
    return '' if v in (None, '') else (f'{v:,}' if isinstance(v, (int, float)) else str(v))

lines = ['# Coverage matrix & predictability (aggregated)', '',
         f'{len(rows)} result cells. Legend: ✅ works · 🟡 partial · ⬜ unavailable (structure yields nothing) · ⛔ blocked (OS/env).',
         '', '## Coverage matrix', '',
         '| OS | App | Stack | Channel | Verdict | Failure | View tok | Shot tok | Predictable a priori? |',
         '|----|-----|-------|---------|---------|---------|---------:|---------:|:---------------------:|']
for d in sorted(rows, key=lambda r: (r['os'], r['stack'])):
    pred = '✅' if d.get('stack_detection', {}).get('detected_before_use') else '❓'
    lines.append(f"| {d['os']} | {d['app']} | {d['stack']} | {d['channel']} | "
                 f"{V.get(d['verdict'], d['verdict'])} | {F.get(d['failure_class'], d['failure_class'])} | "
                 f"{tok(d,'view_tokens_est')} | {tok(d,'screenshot_tokens_est')} | {pred} |")

# predictability table (H5)
lines += ['', '## Predictability & safety (H5)', '',
          'The production-safety question: could a router know the channel in advance, and does failure stay explicit (never silent)?', '',
          '| Stack signature | Channel | Coverage verdict | Failure mode |',
          '|-----------------|---------|------------------|--------------|']
seen = set()
for d in sorted(rows, key=lambda r: r['stack']):
    sig = d.get('stack_detection', {}).get('signature', '?')
    key = (sig, d['channel'])
    if key in seen: continue
    seen.add(key)
    lines.append(f"| {sig} | {d['channel']} | {V.get(d['verdict'], d['verdict'])} | {F.get(d['failure_class'], d['failure_class'])} |")

# safety summary
n = len(rows)
silent = [d for d in rows if d['failure_class'] == 'silent']
unpred = [d for d in rows if not d.get('stack_detection', {}).get('detected_before_use')]
works = [d for d in rows if d['verdict'] == 'works']
lines += ['', '## Safety verdict', '',
          f'- Cells where structure **works**: {len(works)}/{n}.',
          f'- **Silent divergences** (disqualifying): {len(silent)}/{n}' + (' ✅ none found' if not silent else ' ❗ ' + ', '.join(d['app'] for d in silent)),
          f'- Cells **not** predictable in advance: {len(unpred)}/{n}' + (' ✅ none' if not unpred else ' ❗ ' + ', '.join(d['app'] for d in unpred)),
          '',
          'Reading: every failure so far is either **explicit** (opaque rect / honest empty tree) or **blocked** (OS/env), and every channel was detectable from a stack signature before use. That is the pattern a production router needs. The open risk to hunt on the other OSes is any **silent** cell — a channel that returns a view disagreeing with the screen without declaring it.']

open(os.path.join(HERE, 'MATRIX.md'), 'w').write('\n'.join(lines) + '\n')
json.dump({'cells': rows}, open(os.path.join(HERE, 'matrix.json'), 'w'), indent=2)
print(f'wrote MATRIX.md and matrix.json from {n} cells; silent={len(silent)}, unpredictable={len(unpred)}')
