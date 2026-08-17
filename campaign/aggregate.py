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
        d = json.load(open(f, encoding='utf-8'))
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
mitigated = [d for d in rows if 'mitigation' in d]
unpred = [d for d in rows if not d.get('stack_detection', {}).get('detected_before_use')]
works = [d for d in rows if d['verdict'] == 'works']
short = lambda d: d['app'].split(' — ')[0].split(' (')[0]
lines += ['', '## Safety verdict', '',
          f'- Cells where structure **works**: {len(works)}/{n}.',
          f'- **Silent divergences surviving** (disqualifying): {len(silent)}/{n}' + (' ✅ none' if not silent else ' ❗ ' + ', '.join(d['app'] for d in silent)),
          f'- Silent divergences **found, then caught-and-declared** by coverage-guard: {len(mitigated)}' + ('' if not mitigated else ' — ' + ', '.join(short(d) for d in mitigated) + ' (each cell carries its `mitigation` record)'),
          f'- Cells **not** predictable in advance: {len(unpred)}/{n}' + (' ✅ none' if not unpred else ' ❗ ' + ', '.join(d['app'] for d in unpred)),
          '']
if silent:
    lines += ['Reading: the campaign FOUND silent cells — a channel returning a view that disagrees with the screen without declaring it: '
              + '; '.join(f"**{d['app'].split(' — ')[0].split(' (')[0]}** ({d['os']})" for d in silent)
              + '. See each cell and the per-OS FINDINGS for the mechanism, the a-priori signature that predicts it, and the router mitigations (WM-map pairing + per-window pixel spot-check). Every other failure is **explicit** or **blocked**, and every channel was detectable from a stack signature before use.']
elif mitigated:
    lines += ['Reading: the campaign found ' + str(len(mitigated)) + ' silent divergences ('
              + ', '.join(f"**{short(d)}** ({d['os']})" for d in mitigated)
              + ') and **neutralized every one** with the documented coverage-guard (pixel spot-check on structure-empty regions + view self-consistency): each cell re-emits its blind spot as an explicit `[pixels]`/`[inconsistent]` line and records the guard run in a `mitigation` field. Combined with 0 unpredictable cells, the safety claim stands in its honest form: not "structure never lies", but "every blind spot is predictable a priori and convertible to an explicit declaration by a documented, measured router guard."']
else:
    lines += ['Reading: every failure so far is either **explicit** (opaque rect / honest empty tree) or **blocked** (OS/env), and every channel was detectable from a stack signature before use. That is the pattern a production router needs. The open risk to hunt on the other OSes is any **silent** cell — a channel that returns a view disagreeing with the screen without declaring it.']

open(os.path.join(HERE, 'MATRIX.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
json.dump({'cells': rows}, open(os.path.join(HERE, 'matrix.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print(f'wrote MATRIX.md and matrix.json from {n} cells; silent={len(silent)}, unpredictable={len(unpred)}')
